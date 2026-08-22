/** Trusted relay for neutral local API requests; it never exposes pairing material to pages. */

import {
  type ApiClientError,
  BackendApiClient,
  type BackendConfiguration,
} from "./api/client.js";
import type { components } from "./api/generated-contract.js";
import { loadPairedBackendConfiguration } from "./config/pairing.js";

type DiagnosticsResponse = components["schemas"]["DiagnosticsResponse"];
type DraftStateResponse = components["schemas"]["DraftStateResponse"];
type EventRequest = components["schemas"]["EventRequest"];
type EventResponse = components["schemas"]["EventResponse"];
type HealthResponse = components["schemas"]["HealthResponse"];
type LeagueCreateRequest = components["schemas"]["LeagueCreateRequest"];
type LeagueResponse = components["schemas"]["LeagueResponse"];
type RecommendationResponse = components["schemas"]["RecommendationResponse"];
type SnapshotRequest = components["schemas"]["SnapshotRequest"];
type SnapshotResponse = components["schemas"]["SnapshotResponse"];
type DraftCreateRequest = components["schemas"]["DraftCreateRequest"];

export type WorkerRequest =
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "health" | "diagnostics";
    }
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "create_league";
      request: LeagueCreateRequest;
    }
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "create_draft";
      request: DraftCreateRequest;
    }
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "get_draft" | "recommendations";
      draftId: string;
    }
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "ingest_event";
      draftId: string;
      request: EventRequest;
    }
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "reconcile_snapshot";
      draftId: string;
      request: SnapshotRequest;
    };

type WorkerSuccess =
  | HealthResponse
  | DiagnosticsResponse
  | LeagueResponse
  | DraftStateResponse
  | EventResponse
  | SnapshotResponse
  | RecommendationResponse;

export type WorkerResponse =
  | { ok: true; data: WorkerSuccess }
  | {
      ok: false;
      error: {
        kind:
          | "authentication"
          | "conflict"
          | "incompatible"
          | "unavailable"
          | "validation";
        message: string;
        retryable: boolean;
        correlationId?: string;
      };
    };

export interface WorkerDependencies {
  loadConfiguration(): Promise<BackendConfiguration>;
  createClient(configuration: BackendConfiguration): BackendApiClient;
}

const dependencies: WorkerDependencies = {
  loadConfiguration: loadPairedBackendConfiguration,
  createClient: (configuration) => new BackendApiClient({ configuration }),
};

function isWorkerRequest(value: unknown): value is WorkerRequest {
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    value.type === "nfl_fantasy_assistant_backend" &&
    "operation" in value &&
    typeof value.operation === "string"
  );
}

function errorResponse(error: unknown): WorkerResponse {
  if (error instanceof Error && "kind" in error && "retryable" in error) {
    const apiError = error as ApiClientError;
    return {
      ok: false,
      error: {
        kind: apiError.kind,
        message: apiError.message,
        retryable: apiError.retryable,
        correlationId: apiError.correlationId,
      },
    };
  }
  return {
    ok: false,
    error: {
      kind: "unavailable",
      message:
        error instanceof Error
          ? error.message
          : "The local backend is unavailable.",
      retryable: true,
    },
  };
}

export async function handleWorkerRequest(
  request: WorkerRequest,
  injected: WorkerDependencies = dependencies,
): Promise<WorkerResponse> {
  try {
    const client = injected.createClient(await injected.loadConfiguration());
    switch (request.operation) {
      case "health":
        return { ok: true, data: await client.health() };
      case "diagnostics":
        return { ok: true, data: await client.diagnostics() };
      case "create_league":
        return { ok: true, data: await client.createLeague(request.request) };
      case "create_draft":
        return { ok: true, data: await client.createDraft(request.request) };
      case "get_draft":
        return { ok: true, data: await client.getDraft(request.draftId) };
      case "ingest_event":
        return {
          ok: true,
          data: await client.ingestEvent(request.draftId, request.request),
        };
      case "reconcile_snapshot":
        return {
          ok: true,
          data: await client.reconcileSnapshot(
            request.draftId,
            request.request,
          ),
        };
      case "recommendations":
        return {
          ok: true,
          data: await client.recommendations(request.draftId),
        };
    }
  } catch (error) {
    return errorResponse(error);
  }
}

if (typeof chrome !== "undefined") {
  chrome.runtime.onMessage.addListener(
    (message: unknown, sender, sendResponse) => {
      if (sender.id !== chrome.runtime.id || !isWorkerRequest(message)) return;
      void handleWorkerRequest(message).then(sendResponse);
      return true;
    },
  );
}
