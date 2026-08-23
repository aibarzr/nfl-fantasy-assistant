import { describe, expect, it, vi } from "vitest";

import {
  SLEEPER_POLL_INTERVAL_MS,
  SLEEPER_POLL_MAX_BACKOFF_MS,
  startSleeperLiveLoop,
  type SleeperTimer,
} from "../src/content/sleeper-live-loop.js";
import type { RecommendationPanelState } from "../src/ui/panel.js";

const draftId = "draft-local";
const pageUrl = "https://sleeper.com/draft/nfl/draft-fixture";

function timerCapture(): {
  timer: SleeperTimer;
  delays: number[];
  callbacks: Array<() => void>;
} {
  const delays: number[] = [];
  const callbacks: Array<() => void> = [];
  return {
    delays,
    callbacks,
    timer: {
      setTimeout: (callback, delayMs) => {
        callbacks.push(callback);
        delays.push(delayMs);
        return callbacks.length;
      },
      clearTimeout: () => undefined,
    },
  };
}

function currentRecommendation(): object {
  return {
    status: "current",
    draft_id: draftId,
    revision: 0,
    generated_at: "2026-08-23T00:00:00Z",
    dataset_version: "dataset-fixture",
    feature_version: "feature-fixture",
    model_version: "projection-v3",
    source_updated_at: {},
    candidates: [],
  };
}

describe("Sleeper live recovery loop", () => {
  it("reconciles then renders current backend recommendations at the bounded base interval", async () => {
    const { timer, delays, callbacks } = timerCapture();
    const states: RecommendationPanelState[] = [];
    const sendMessage = vi.fn(async (message: { operation: string }) => {
      if (message.operation === "sleeper_sync") {
        return {
          ok: true,
          data: {
            outcome: "identical",
            draft: { status: "active", reconciliation_state: "current" },
          },
        };
      }
      return { ok: true, data: currentRecommendation() };
    });

    startSleeperLiveLoop(
      draftId,
      pageUrl,
      { render: (state) => void states.push(state) },
      sendMessage,
      timer,
    );
    expect(delays).toEqual([SLEEPER_POLL_INTERVAL_MS]);

    callbacks[0]?.();
    await vi.waitFor(() => expect(sendMessage).toHaveBeenCalledTimes(2));

    expect(sendMessage.mock.calls[0]?.[0]).toMatchObject({
      operation: "sleeper_sync",
      draftId,
      pageUrl,
    });
    expect(sendMessage.mock.calls[1]?.[0]).toEqual({
      type: "nfl_fantasy_assistant_backend",
      operation: "recommendations",
      draftId,
    });
    expect(states.at(-1)).toMatchObject({ kind: "current" });
    expect(delays.at(-1)).toBe(SLEEPER_POLL_INTERVAL_MS);
  });

  it("renders a non-current failure and doubles the next interval", async () => {
    const { timer, delays, callbacks } = timerCapture();
    const states: RecommendationPanelState[] = [];

    startSleeperLiveLoop(
      draftId,
      pageUrl,
      { render: (state) => void states.push(state) },
      async () => ({
        ok: false,
        error: {
          kind: "unavailable",
          message: "Sleeper is throttling recovery.",
          retryable: true,
        },
      }),
      timer,
    );
    callbacks[0]?.();
    await vi.waitFor(() => expect(states).toHaveLength(1));

    expect(states[0]).toMatchObject({ kind: "disconnected", retryable: true });
    expect(delays).toEqual([
      SLEEPER_POLL_INTERVAL_MS,
      SLEEPER_POLL_INTERVAL_MS * 2,
    ]);
  });

  it("caps repeated failure backoff and can be stopped", async () => {
    const { timer, delays, callbacks } = timerCapture();
    const loop = startSleeperLiveLoop(
      draftId,
      pageUrl,
      { render: () => undefined },
      async () => ({
        ok: false,
        error: { kind: "unavailable", message: "Unavailable", retryable: true },
      }),
      timer,
    );

    for (let index = 0; index < 5; index += 1) {
      callbacks[index]?.();
      await vi.waitFor(() => expect(delays).toHaveLength(index + 2));
    }
    expect(delays.at(-1)).toBe(SLEEPER_POLL_MAX_BACKOFF_MS);
    loop.stop();
  });
});
