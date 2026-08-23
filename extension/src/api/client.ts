/** Checked, service-worker-only transport for the neutral local v1 API. */

import type { components } from "./generated-contract.js";

export type ApiErrorKind =
  | "authentication"
  | "conflict"
  | "incompatible"
  | "unavailable"
  | "validation";

export class ApiClientError extends Error {
  constructor(
    readonly kind: ApiErrorKind,
    message: string,
    readonly retryable: boolean,
    readonly correlationId?: string,
  ) {
    super(message);
  }
}

export interface BackendConfiguration {
  baseUrl: string;
  bearerToken: string;
}

export interface ApiClientOptions {
  configuration: BackendConfiguration;
  fetcher?: typeof fetch;
  timeoutMs?: number;
}

type DiagnosticsResponse = components["schemas"]["DiagnosticsResponse"];
type DraftCreateRequest = components["schemas"]["DraftCreateRequest"];
type DraftStateResponse = components["schemas"]["DraftStateResponse"];
type EventRequest = components["schemas"]["EventRequest"];
type EventResponse = components["schemas"]["EventResponse"];
type HealthResponse = components["schemas"]["HealthResponse"];
type LeagueCreateRequest = components["schemas"]["LeagueCreateRequest"];
type LeagueResponse = components["schemas"]["LeagueResponse"];
type RecommendationResponse = components["schemas"]["RecommendationResponse"];
type SnapshotRequest = components["schemas"]["SnapshotRequest"];
type SnapshotResponse = components["schemas"]["SnapshotResponse"];

interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
    retryable?: boolean;
  };
}

const API_VERSION = "v1";
const DEFAULT_TIMEOUT_MS = 2_000;

function endpoint(baseUrl: string, path: string): string {
  return new URL(path, `${baseUrl.replace(/\/$/, "")}/`).toString();
}

function classify(status: number, code?: string): ApiErrorKind {
  if (status === 401 || status === 403) return "authentication";
  if (status === 409) return "conflict";
  if (status === 422 || status === 400) return "validation";
  if (code === "incompatible_api") return "incompatible";
  return "unavailable";
}

function requestId(): string {
  return `ext_${crypto.randomUUID()}`;
}

export class BackendApiClient {
  private readonly fetcher: typeof fetch;
  private readonly timeoutMs: number;

  constructor(private readonly options: ApiClientOptions) {
    this.fetcher = options.fetcher ?? fetch;
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  async health(): Promise<HealthResponse> {
    const response = await this.request<HealthResponse>(
      "/v1/health",
      { method: "GET" },
      true,
    );
    if (response.api_version !== API_VERSION) {
      throw new ApiClientError(
        "incompatible",
        "The local backend API version is incompatible with this extension.",
        false,
      );
    }
    return response;
  }

  diagnostics(): Promise<DiagnosticsResponse> {
    return this.request("/v1/diagnostics", { method: "GET" }, true);
  }

  createLeague(request: LeagueCreateRequest): Promise<LeagueResponse> {
    return this.request("/v1/leagues", this.json("POST", request), false);
  }

  createDraft(request: DraftCreateRequest): Promise<DraftStateResponse> {
    return this.request("/v1/drafts", this.json("POST", request), false);
  }

  getDraft(draftId: string): Promise<DraftStateResponse> {
    return this.request(
      `/v1/drafts/${encodeURIComponent(draftId)}`,
      { method: "GET" },
      true,
    );
  }

  ingestEvent(draftId: string, request: EventRequest): Promise<EventResponse> {
    return this.request(
      `/v1/drafts/${encodeURIComponent(draftId)}/events`,
      this.json("POST", request),
      true,
    );
  }

  reconcileSnapshot(
    draftId: string,
    request: SnapshotRequest,
  ): Promise<SnapshotResponse> {
    return this.request(
      `/v1/drafts/${encodeURIComponent(draftId)}/snapshot`,
      this.json("POST", request),
      false,
    );
  }

  recommendations(draftId: string): Promise<RecommendationResponse> {
    return this.request(
      `/v1/drafts/${encodeURIComponent(draftId)}/recommendations`,
      { method: "GET" },
      true,
    );
  }

  private json(method: "POST", body: object): RequestInit {
    return { method, body: JSON.stringify(body) };
  }

  private async request<Response>(
    path: string,
    init: RequestInit,
    retrySafe: boolean,
  ): Promise<Response> {
    const attempts = retrySafe ? 2 : 1;
    let failure: ApiClientError | undefined;
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      try {
        return await this.once<Response>(path, init);
      } catch (error) {
        if (!(error instanceof ApiClientError)) throw error;
        failure = error;
        if (!error.retryable || attempt + 1 === attempts) throw error;
      }
    }
    throw (
      failure ??
      new ApiClientError("unavailable", "Backend request failed.", true)
    );
  }

  private async once<Response>(
    path: string,
    init: RequestInit,
  ): Promise<Response> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetcher.call(
        globalThis,
        endpoint(this.options.configuration.baseUrl, path),
        {
          ...init,
          credentials: "omit",
          headers: {
            Authorization: `Bearer ${this.options.configuration.bearerToken}`,
            "Content-Type": "application/json",
            "X-Request-ID": requestId(),
            ...init.headers,
          },
          signal: controller.signal,
        },
      );
      const payload = (await response.json().catch(() => ({}))) as Response &
        ErrorEnvelope;
      if (response.ok) return payload;
      throw new ApiClientError(
        classify(response.status, payload.error?.code),
        payload.error?.message ?? "The backend returned an invalid response.",
        payload.error?.retryable ?? response.status >= 500,
        payload.error?.request_id,
      );
    } catch (error) {
      if (error instanceof ApiClientError) throw error;
      throw new ApiClientError(
        "unavailable",
        "The local backend is unavailable.",
        true,
      );
    } finally {
      clearTimeout(timeout);
    }
  }
}
