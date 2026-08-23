/** Page-side renderer that asks the worker for fresh backend state after every reload. */

import type { WorkerResponse } from "../service-worker.js";
import {
  RecommendationPanel,
  type RecommendationResponse,
  stateFromApiError,
} from "../ui/panel.js";

export type SendRecommendationMessage = (message: {
  type: "nfl_fantasy_assistant_backend";
  operation: "recommendations";
  draftId: string;
}) => Promise<unknown>;

export interface RecommendationPanelRenderer {
  render(state: Parameters<RecommendationPanel["render"]>[0]): void;
}

function isRecommendation(value: unknown): value is RecommendationResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    value.status === "current" &&
    "candidates" in value &&
    Array.isArray(value.candidates)
  );
}

export async function renderRecommendations(
  draftId: string,
  panel: RecommendationPanelRenderer = new RecommendationPanel(),
  sendMessage: SendRecommendationMessage = (message) =>
    chrome.runtime.sendMessage(message),
): Promise<RecommendationPanelRenderer> {
  panel.render({
    kind: "loading",
    detail: "Requesting the latest canonical draft state.",
  });
  const response = (await sendMessage({
    type: "nfl_fantasy_assistant_backend",
    operation: "recommendations",
    draftId,
  })) as WorkerResponse;
  if (!response.ok) {
    panel.render(stateFromApiError(response.error));
  } else if (isRecommendation(response.data)) {
    panel.render({ kind: "current", recommendation: response.data });
  } else {
    panel.render({
      kind: "error",
      detail:
        "The local backend returned an unexpected recommendation response.",
      retryable: false,
    });
  }
  return panel;
}
