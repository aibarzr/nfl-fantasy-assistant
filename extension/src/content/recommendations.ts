/** Page-side renderer that asks the worker for fresh backend state after every reload. */

import type { WorkerResponse } from "../service-worker.js";
import {
  RecommendationPanel,
  type RecommendationResponse,
  stateFromApiError,
} from "../ui/panel.js";

export type SendRecommendationMessage = (
  message:
    | {
        type: "nfl_fantasy_assistant_backend";
        operation: "recommendations";
        draftId: string;
      }
    | {
        type: "nfl_fantasy_assistant_backend";
        operation: "sleeper_player_labels";
        externalIds: string[];
      },
) => Promise<unknown>;

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

function isLabels(value: unknown): value is Record<string, string> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.values(value).every((label) => typeof label === "string")
  );
}

async function sleeperLabels(
  recommendation: RecommendationResponse,
  sendMessage: SendRecommendationMessage,
): Promise<Record<string, string>> {
  const externalIds = recommendation.candidates
    .filter((candidate) => candidate.provider === "sleeper")
    .map((candidate) => candidate.external_id);
  if (externalIds.length === 0) return {};
  try {
    const response = (await sendMessage({
      type: "nfl_fantasy_assistant_backend",
      operation: "sleeper_player_labels",
      externalIds,
    })) as WorkerResponse;
    return response.ok && isLabels(response.data) ? response.data : {};
  } catch {
    return {};
  }
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
    panel.render({
      kind: "current",
      recommendation: response.data,
      labels: await sleeperLabels(response.data, sendMessage),
    });
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
