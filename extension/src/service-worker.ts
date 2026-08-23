/** Trusted relay for neutral local API requests; it never exposes pairing material to pages. */

import {
  ApiClientError,
  BackendApiClient,
  type BackendConfiguration,
} from "./api/client.js";
import type { components } from "./api/generated-contract.js";
import { detectSleeperDraftSurface } from "./adapters/sleeper/surface.js";
import {
  fetchSleeperInitializationSnapshot,
  fetchSleeperPlayerLabels,
  fetchSleeperRecoverySnapshot,
} from "./adapters/sleeper/api.js";
import type { SleeperInitializationResult } from "./adapters/sleeper/initial-snapshot.js";
import type { SleeperRecoveryResult } from "./adapters/sleeper/recovery-snapshot.js";
import {
  loadSleeperInitializationConfiguration,
  type SleeperInitializationConfiguration,
} from "./config/sleeper-initialization.js";
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
type SleeperPlayerLabels = Record<string, string>;

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
    }
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "sleeper_recovery";
      pageUrl: string;
      observedAt: string;
    }
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "sleeper_initialize";
      pageUrl: string;
      observedAt: string;
    }
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "sleeper_player_labels";
      externalIds: string[];
    }
  | {
      type: "nfl_fantasy_assistant_backend";
      operation: "sleeper_sync";
      draftId: string;
      pageUrl: string;
      observedAt: string;
    };

type WorkerSuccess =
  | HealthResponse
  | DiagnosticsResponse
  | LeagueResponse
  | DraftStateResponse
  | EventResponse
  | SnapshotResponse
  | RecommendationResponse
  | SleeperPlayerLabels;

type SleeperRecoveryResponse = Extract<
  SleeperRecoveryResult,
  { status: "ready" }
>;

export type WorkerResponse =
  | { ok: true; data: WorkerSuccess | SleeperRecoveryResponse }
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
  fetchSleeperRecovery?(
    pageUrl: string,
    observedAt: string,
  ): Promise<SleeperRecoveryResult>;
  loadSleeperInitializationConfiguration?(): Promise<SleeperInitializationConfiguration>;
  fetchSleeperInitialization?(
    pageUrl: string,
    observedAt: string,
    context: SleeperInitializationConfiguration,
  ): Promise<SleeperInitializationResult>;
  fetchSleeperPlayerLabels?(
    externalIds: readonly string[],
  ): Promise<Record<string, string>>;
}

const dependencies: WorkerDependencies = {
  loadConfiguration: loadPairedBackendConfiguration,
  createClient: (configuration) => new BackendApiClient({ configuration }),
  fetchSleeperRecovery: (pageUrl, observedAt) =>
    fetchSleeperRecoverySnapshot(pageUrl, observedAt),
  loadSleeperInitializationConfiguration,
  fetchSleeperInitialization: (pageUrl, observedAt, context) =>
    fetchSleeperInitializationSnapshot(pageUrl, observedAt, context),
  fetchSleeperPlayerLabels,
};

const SLEEPER_PAGE_URL_MAX_LENGTH = 2_048;
const DRAFT_ID_MAX_LENGTH = 256;
const SLEEPER_LABEL_REQUEST_MAX = 12;
const SLEEPER_EXTERNAL_ID_MAX_LENGTH = 128;
const sleeperLabelCache = new Map<string, string>();

export function isWorkerRequest(value: unknown): value is WorkerRequest {
  if (
    typeof value !== "object" ||
    value === null ||
    !("type" in value) ||
    value.type !== "nfl_fantasy_assistant_backend" ||
    !("operation" in value) ||
    typeof value.operation !== "string"
  ) {
    return false;
  }
  if (value.operation === "sleeper_player_labels") {
    return (
      "externalIds" in value &&
      Array.isArray(value.externalIds) &&
      value.externalIds.length <= SLEEPER_LABEL_REQUEST_MAX &&
      value.externalIds.every(
        (externalId) =>
          typeof externalId === "string" &&
          externalId.length > 0 &&
          externalId.length <= SLEEPER_EXTERNAL_ID_MAX_LENGTH,
      )
    );
  }
  if (
    value.operation !== "sleeper_recovery" &&
    value.operation !== "sleeper_initialize" &&
    value.operation !== "sleeper_sync"
  ) {
    return true;
  }
  const hasValidSurface =
    "pageUrl" in value &&
    typeof value.pageUrl === "string" &&
    value.pageUrl.length <= SLEEPER_PAGE_URL_MAX_LENGTH &&
    detectSleeperDraftSurface(value.pageUrl).supported &&
    "observedAt" in value &&
    typeof value.observedAt === "string" &&
    Number.isFinite(Date.parse(value.observedAt));
  return (
    hasValidSurface &&
    (value.operation !== "sleeper_sync" ||
      ("draftId" in value &&
        typeof value.draftId === "string" &&
        value.draftId.length > 0 &&
        value.draftId.length <= DRAFT_ID_MAX_LENGTH))
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

function traceWorkerResponse(
  request: WorkerRequest,
  response: WorkerResponse,
): void {
  if (request.operation === "sleeper_sync" && response.ok) return;
  console.info("[NFL Fantasy Assistant] worker relay", {
    operation: request.operation,
    outcome: response.ok ? "success" : "failure",
    ...(response.ok ? {} : { errorKind: response.error.kind }),
  });
}

function sleeperRuntimeIsReady(diagnostics: DiagnosticsResponse): boolean {
  return (
    diagnostics.data.status === "ready" &&
    diagnostics.identity.status === "ready"
  );
}

export async function handleWorkerRequest(
  request: WorkerRequest,
  injected: WorkerDependencies = dependencies,
): Promise<WorkerResponse> {
  try {
    if (request.operation === "sleeper_player_labels") {
      const missing = request.externalIds.filter(
        (externalId) => !sleeperLabelCache.has(externalId),
      );
      if (missing.length > 0) {
        const labels = await (
          injected.fetchSleeperPlayerLabels ?? fetchSleeperPlayerLabels
        )(missing);
        for (const [externalId, label] of Object.entries(labels)) {
          if (request.externalIds.includes(externalId)) {
            sleeperLabelCache.set(externalId, label);
          }
        }
      }
      return {
        ok: true,
        data: Object.fromEntries(
          request.externalIds.flatMap((externalId) => {
            const label = sleeperLabelCache.get(externalId);
            return label ? [[externalId, label]] : [];
          }),
        ),
      };
    }
    if (request.operation === "sleeper_recovery") {
      await injected.loadConfiguration();
      const recovery = await (
        injected.fetchSleeperRecovery ?? fetchSleeperRecoverySnapshot
      )(request.pageUrl, request.observedAt);
      if (recovery.status !== "ready") {
        return {
          ok: false,
          error: {
            kind: "validation",
            message: recovery.detail,
            retryable: false,
          },
        };
      }
      return { ok: true, data: recovery };
    }
    const client = injected.createClient(await injected.loadConfiguration());
    switch (request.operation) {
      case "sleeper_sync": {
        const diagnostics = await client.diagnostics();
        if (!sleeperRuntimeIsReady(diagnostics)) {
          return {
            ok: false,
            error: {
              kind: "unavailable",
              message:
                "The local backend has no ready prepared data and exact identity mapping for Sleeper recovery.",
              retryable: false,
            },
          };
        }
        const state = await client.getDraft(request.draftId);
        const recovery = await (
          injected.fetchSleeperRecovery ?? fetchSleeperRecoverySnapshot
        )(request.pageUrl, request.observedAt);
        if (recovery.status !== "ready") {
          return {
            ok: false,
            error: {
              kind: "validation",
              message: recovery.detail,
              retryable: false,
            },
          };
        }
        for (
          let index = state.accepted_picks;
          index < recovery.request.picks.length;
          index += 1
        ) {
          const pick = recovery.request.picks[index];
          const eventId = recovery.eventIds[index];
          if (!pick || !eventId) {
            return {
              ok: false,
              error: {
                kind: "validation",
                message:
                  "Sleeper recovery has no stable event ID for an observed pick.",
                retryable: false,
              },
            };
          }
          try {
            await client.ingestEvent(request.draftId, {
              event_id: eventId,
              observed_at: recovery.request.observed_at,
              surface: "sleeper",
              league_provider: "sleeper",
              type: "player_drafted",
              pick,
              protocol_version: "v1",
            });
          } catch (error) {
            if (
              !(error instanceof ApiClientError) ||
              (error.kind !== "conflict" && error.kind !== "validation")
            ) {
              throw error;
            }
          }
        }
        return {
          ok: true,
          data: await client.reconcileSnapshot(
            request.draftId,
            recovery.request,
          ),
        };
      }
      case "sleeper_initialize": {
        const diagnostics = await client.diagnostics();
        if (!sleeperRuntimeIsReady(diagnostics)) {
          return {
            ok: false,
            error: {
              kind: "unavailable",
              message:
                "The local backend has no ready prepared data and exact identity mapping for Sleeper initialization.",
              retryable: false,
            },
          };
        }
        const context = await (
          injected.loadSleeperInitializationConfiguration ??
          loadSleeperInitializationConfiguration
        )();
        const initialization = await (
          injected.fetchSleeperInitialization ??
          fetchSleeperInitializationSnapshot
        )(request.pageUrl, request.observedAt, context);
        if (initialization.status !== "ready") {
          return {
            ok: false,
            error: {
              kind: "validation",
              message: initialization.detail,
              retryable: false,
            },
          };
        }
        const league = await client.createLeague(initialization.leagueRequest);
        return {
          ok: true,
          data: await client.createDraft({
            ...initialization.draftRequest,
            league_id: league.league_id,
          }),
        };
      }
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
      void handleWorkerRequest(message).then((response) => {
        traceWorkerResponse(message, response);
        sendResponse(response);
      });
      return true;
    },
  );
}
