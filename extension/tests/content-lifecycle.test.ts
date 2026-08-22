import { describe, expect, it, vi } from "vitest";

import {
  startEspnContentLifecycle,
  type RecommendationPanelController,
} from "../src/content/lifecycle.js";
import type { RecommendationPanelState } from "../src/ui/panel.js";

const supportedUrl = "https://fantasy.espn.com/football/draft";

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
