/** Poll the validated Sleeper recovery source without making the content script a state owner. */

import type { WorkerResponse } from "../service-worker.js";
import {
  stateFromApiError,
  type RecommendationPanelState,
} from "../ui/panel.js";
import {
  renderRecommendations,
  type RecommendationPanelRenderer,
  type SendRecommendationMessage,
} from "./recommendations.js";

export const SLEEPER_POLL_INTERVAL_MS = 5_000;
export const SLEEPER_POLL_MAX_BACKOFF_MS = 60_000;

export type SendSleeperSyncMessage = SendRecommendationMessage &
  ((message: {
    type: "nfl_fantasy_assistant_backend";
    operation: "sleeper_sync";
    draftId: string;
    pageUrl: string;
    observedAt: string;
  }) => Promise<unknown>);

export interface SleeperLiveLoop {
  stop(): void;
}

export interface SleeperTimer {
  setTimeout(
    callback: () => void,
    delayMs: number,
  ): ReturnType<typeof setTimeout>;
  clearTimeout(timer: ReturnType<typeof setTimeout>): void;
}

const defaultTimer: SleeperTimer = {
  setTimeout: (callback, delayMs) => setTimeout(callback, delayMs),
  clearTimeout: (timer) => clearTimeout(timer),
};

function isSnapshotResponse(value: unknown): value is {
  draft: { status: string; reconciliation_state: string };
} {
  return (
    typeof value === "object" &&
    value !== null &&
    "draft" in value &&
    typeof value.draft === "object" &&
    value.draft !== null &&
    "status" in value.draft &&
    "reconciliation_state" in value.draft &&
    typeof value.draft.status === "string" &&
    typeof value.draft.reconciliation_state === "string"
  );
}

function nonCurrentState(
  detail: string,
  retryable: boolean,
): RecommendationPanelState {
  return { kind: "disconnected", detail, retryable };
}

export function startSleeperLiveLoop(
  draftId: string,
  pageUrl: string,
  panel: RecommendationPanelRenderer,
  sendMessage: SendSleeperSyncMessage = (message) =>
    chrome.runtime.sendMessage(message),
  timer: SleeperTimer = defaultTimer,
): SleeperLiveLoop {
  let stopped = false;
  let scheduled: ReturnType<typeof setTimeout> | undefined;
  let delayMs = SLEEPER_POLL_INTERVAL_MS;

  const schedule = () => {
    if (!stopped)
      scheduled = timer.setTimeout(() => void synchronize(), delayMs);
  };

  const synchronize = async () => {
    try {
      const response = (await sendMessage({
        type: "nfl_fantasy_assistant_backend",
        operation: "sleeper_sync",
        draftId,
        pageUrl,
        observedAt: new Date().toISOString(),
      })) as WorkerResponse;
      if (!response.ok) {
        panel.render(stateFromApiError(response.error));
        delayMs = Math.min(delayMs * 2, SLEEPER_POLL_MAX_BACKOFF_MS);
      } else if (!isSnapshotResponse(response.data)) {
        panel.render(
          nonCurrentState(
            "The local backend returned an unexpected draft recovery response.",
            false,
          ),
        );
        delayMs = Math.min(delayMs * 2, SLEEPER_POLL_MAX_BACKOFF_MS);
      } else if (
        response.data.draft.status === "blocked" ||
        response.data.draft.status === "reconciling" ||
        response.data.draft.reconciliation_state !== "current"
      ) {
        panel.render({
          kind: "blocked",
          detail:
            "Sleeper recovery needs reconciliation before recommendations can be current.",
        });
        delayMs = SLEEPER_POLL_INTERVAL_MS;
      } else {
        await renderRecommendations(draftId, panel, sendMessage);
        delayMs = SLEEPER_POLL_INTERVAL_MS;
      }
    } catch {
      panel.render(
        nonCurrentState(
          "The Sleeper recovery loop is temporarily unavailable.",
          true,
        ),
      );
      delayMs = Math.min(delayMs * 2, SLEEPER_POLL_MAX_BACKOFF_MS);
    }
    schedule();
  };

  schedule();
  return {
    stop: () => {
      stopped = true;
      if (scheduled !== undefined) timer.clearTimeout(scheduled);
    },
  };
}
