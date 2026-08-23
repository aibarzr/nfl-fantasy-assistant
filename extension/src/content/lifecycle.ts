/** Mount the read-only draft board only on the exact supported ESPN surface. */

import { detectEspnDraftSurface } from "../adapters/espn/surface.js";
import { detectSleeperDraftSurface } from "../adapters/sleeper/surface.js";
import type { WorkerResponse } from "../service-worker.js";
import { RecommendationPanel, stateFromApiError } from "../ui/panel.js";
import type { RecommendationPanelState } from "../ui/panel.js";

type SendMessage = (message: {
  type: string;
  operation: "health" | "sleeper_recovery";
  pageUrl?: string;
  observedAt?: string;
}) => Promise<unknown>;

export interface RecommendationPanelController {
  render(state: RecommendationPanelState): void;
}

type CreatePanel = (target?: HTMLElement) => RecommendationPanelController;

function isHealthResponse(
  value: unknown,
): value is { status: string; api_version: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    "api_version" in value &&
    typeof value.status === "string" &&
    typeof value.api_version === "string"
  );
}

export async function startEspnContentLifecycle(
  pageUrl = window.location.href,
  target?: HTMLElement,
  sendMessage: SendMessage = (message) => chrome.runtime.sendMessage(message),
  createPanel: CreatePanel = (mountTarget) =>
    new RecommendationPanel(mountTarget ?? document.body),
): Promise<RecommendationPanelController | undefined> {
  if (!detectEspnDraftSurface(pageUrl).supported) return undefined;

  const panel = createPanel(target);
  panel.render({
    kind: "loading",
    detail:
      "Checking the paired local backend before ESPN draft initialization.",
  });
  const response = (await sendMessage({
    type: "nfl_fantasy_assistant_backend",
    operation: "health",
  })) as WorkerResponse;
  if (!response.ok) {
    panel.render(stateFromApiError(response.error));
  } else if (
    isHealthResponse(response.data) &&
    response.data.api_version === "v1"
  ) {
    panel.render({
      kind: "empty",
      detail:
        "Connected to the local backend. Waiting for a validated ESPN draft initialization.",
    });
  } else {
    panel.render({
      kind: "incompatible",
      detail:
        "The local backend API version is incompatible with this extension.",
      retryable: false,
    });
  }
  return panel;
}

export async function startSleeperContentLifecycle(
  pageUrl = window.location.href,
  target?: HTMLElement,
  sendMessage: SendMessage = (message) => chrome.runtime.sendMessage(message),
  createPanel: CreatePanel = (mountTarget) =>
    new RecommendationPanel(mountTarget ?? document.body),
): Promise<RecommendationPanelController | undefined> {
  if (!detectSleeperDraftSurface(pageUrl).supported) return undefined;

  const panel = createPanel(target);
  panel.render({
    kind: "loading",
    detail:
      "Checking the paired local backend before Sleeper draft initialization.",
  });
  const response = (await sendMessage({
    type: "nfl_fantasy_assistant_backend",
    operation: "health",
  })) as WorkerResponse;
  if (!response.ok) {
    panel.render(stateFromApiError(response.error));
  } else if (
    isHealthResponse(response.data) &&
    response.data.api_version === "v1"
  ) {
    const recovery = (await sendMessage({
      type: "nfl_fantasy_assistant_backend",
      operation: "sleeper_recovery",
      pageUrl,
      observedAt: new Date().toISOString(),
    })) as WorkerResponse;
    if (!recovery.ok) {
      panel.render(stateFromApiError(recovery.error));
    } else {
      panel.render({
        kind: "empty",
        detail:
          "Validated the current Sleeper recovery snapshot. Waiting for the prepared-pool identity gate before initialization.",
      });
    }
  } else {
    panel.render({
      kind: "incompatible",
      detail:
        "The local backend API version is incompatible with this extension.",
      retryable: false,
    });
  }
  return panel;
}
