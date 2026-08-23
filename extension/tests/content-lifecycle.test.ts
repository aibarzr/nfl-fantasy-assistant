import { describe, expect, it, vi } from "vitest";

import {
  startEspnContentLifecycle,
  startSleeperContentLifecycle,
  type RecommendationPanelController,
} from "../src/content/lifecycle.js";
import type { RecommendationPanelState } from "../src/ui/panel.js";

const supportedUrl = "https://fantasy.espn.com/football/draft";
const sleeperUrl = "https://sleeper.com/draft/nfl/draft-fixture";

function panelCapture(): {
  panel: RecommendationPanelController;
  states: RecommendationPanelState[];
} {
  const states: RecommendationPanelState[] = [];
  return { panel: { render: (state) => void states.push(state) }, states };
}

describe("ESPN content lifecycle", () => {
  it("does not mount or call the worker on an unsupported surface", async () => {
    const sendMessage = vi.fn();
    const createPanel = vi.fn();

    await expect(
      startEspnContentLifecycle(
        "https://fantasy.espn.com/football/league",
        undefined,
        sendMessage,
        createPanel,
      ),
    ).resolves.toBeUndefined();
    expect(sendMessage).not.toHaveBeenCalled();
    expect(createPanel).not.toHaveBeenCalled();
  });

  it("mounts a visibly non-current status until a validated draft can be initialized", async () => {
    const { panel, states } = panelCapture();

    await startEspnContentLifecycle(
      supportedUrl,
      undefined,
      async () => ({ ok: true, data: { status: "ok", api_version: "v1" } }),
      () => panel,
    );

    expect(states).toEqual([
      {
        kind: "loading",
        detail:
          "Checking the paired local backend before ESPN draft initialization.",
      },
      {
        kind: "empty",
        detail:
          "Connected to the local backend. Waiting for a validated ESPN draft initialization.",
      },
    ]);
  });

  it("renders an explicit non-current error from the worker", async () => {
    const { panel, states } = panelCapture();

    await startEspnContentLifecycle(
      supportedUrl,
      undefined,
      async () => ({
        ok: false,
        error: {
          kind: "authentication",
          message: "Pair again.",
          retryable: false,
        },
      }),
      () => panel,
    );

    expect(states.at(-1)).toMatchObject({
      kind: "unauthorized",
      detail: "Pair again.",
    });
  });
});

describe("Sleeper content lifecycle", () => {
  it("does not mount or request provider data on a non-draft Sleeper page", async () => {
    const sendMessage = vi.fn();
    const createPanel = vi.fn();

    await expect(
      startSleeperContentLifecycle(
        "https://sleeper.com/leagues/league-fixture",
        undefined,
        sendMessage,
        createPanel,
      ),
    ).resolves.toBeUndefined();
    expect(sendMessage).not.toHaveBeenCalled();
    expect(createPanel).not.toHaveBeenCalled();
  });

  it("uses the service worker recovery path but leaves initialization blocked by identity coverage", async () => {
    const { panel, states } = panelCapture();
    const sendMessage = vi.fn(async (message: { operation: string }) => {
      if (message.operation === "health") {
        return { ok: true, data: { status: "ok", api_version: "v1" } };
      }
      return {
        ok: true,
        data: {
          status: "ready",
          request: {
            source: "sleeper_api",
            observed_at: "2026-08-23T00:00:00Z",
            declared_complete: true,
            picks: [],
          },
          eventIds: [],
        },
      };
    });

    await startSleeperContentLifecycle(
      sleeperUrl,
      undefined,
      sendMessage,
      () => panel,
    );

    expect(sendMessage).toHaveBeenNthCalledWith(1, {
      type: "nfl_fantasy_assistant_backend",
      operation: "health",
    });
    expect(sendMessage).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        type: "nfl_fantasy_assistant_backend",
        operation: "sleeper_recovery",
        pageUrl: sleeperUrl,
      }),
    );
    expect(states.at(-1)).toMatchObject({
      kind: "empty",
      detail: expect.stringContaining("prepared-pool identity gate"),
    });
  });

  it("renders an error and never offers initialization when the recovery snapshot is invalid", async () => {
    const { panel, states } = panelCapture();
    const sendMessage = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        data: { status: "ok", api_version: "v1" },
      })
      .mockResolvedValueOnce({
        ok: false,
        error: {
          kind: "validation",
          message: "Unsafe Sleeper snapshot.",
          retryable: false,
        },
      });

    await startSleeperContentLifecycle(
      sleeperUrl,
      undefined,
      sendMessage,
      () => panel,
    );

    expect(states.at(-1)).toMatchObject({
      kind: "error",
      detail: "Unsafe Sleeper snapshot.",
    });
  });
});
