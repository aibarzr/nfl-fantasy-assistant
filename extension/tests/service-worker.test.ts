import { describe, expect, it, vi } from "vitest";

import { BackendApiClient } from "../src/api/client.js";
import { handleWorkerRequest, isWorkerRequest } from "../src/service-worker.js";

const configuration = {
  baseUrl: "http://127.0.0.1:8765",
  bearerToken: "a".repeat(43),
};

describe("service-worker relay", () => {
  it("accepts a Sleeper recovery request only for the exact supported surface", () => {
    expect(
      isWorkerRequest({
        type: "nfl_fantasy_assistant_backend",
        operation: "sleeper_recovery",
        pageUrl: "https://sleeper.com/draft/nfl/draft-fixture",
        observedAt: "2026-08-23T00:00:00Z",
      }),
    ).toBe(true);
    expect(
      isWorkerRequest({
        type: "nfl_fantasy_assistant_backend",
        operation: "sleeper_recovery",
        pageUrl: "https://sleeper.com/leagues/league-fixture",
        observedAt: "2026-08-23T00:00:00Z",
      }),
    ).toBe(false);
    expect(
      isWorkerRequest({
        type: "nfl_fantasy_assistant_backend",
        operation: "sleeper_initialize",
        pageUrl: "https://sleeper.com/draft/nfl/draft-fixture",
        observedAt: "2026-08-23T00:00:00Z",
      }),
    ).toBe(true);
  });

  it("loads current configuration for every request so restart and token rotation need no memory", async () => {
    const configurations = [
      configuration,
      { ...configuration, bearerToken: "b".repeat(43) },
    ];
    const usedTokens: string[] = [];
    let index = 0;
    const dependencies = {
      loadConfiguration: async () => configurations[index++] ?? configuration,
      createClient: (current: typeof configuration) => {
        usedTokens.push(current.bearerToken);
        return new BackendApiClient({
          configuration: current,
          fetcher: async () =>
            new Response(JSON.stringify({ status: "ok", api_version: "v1" }), {
              status: 200,
            }),
        });
      },
    };

    await expect(
      handleWorkerRequest(
        { type: "nfl_fantasy_assistant_backend", operation: "health" },
        dependencies,
      ),
    ).resolves.toMatchObject({ ok: true });
    await expect(
      handleWorkerRequest(
        { type: "nfl_fantasy_assistant_backend", operation: "health" },
        dependencies,
      ),
    ).resolves.toMatchObject({ ok: true });
    expect(usedTokens).toEqual(["a".repeat(43), "b".repeat(43)]);
  });

  it("returns actionable unavailable configuration errors without returning the stored token", async () => {
    const response = await handleWorkerRequest(
      { type: "nfl_fantasy_assistant_backend", operation: "diagnostics" },
      {
        loadConfiguration: async () => {
          throw new Error(
            "The extension is not paired. Pair it from service-worker tools.",
          );
        },
        createClient: () => {
          throw new Error("not reached");
        },
      },
    );
    expect(response).toMatchObject({
      ok: false,
      error: { kind: "unavailable", retryable: true },
    });
    expect(JSON.stringify(response)).not.toContain("a".repeat(43));
  });

  it("reads a validated Sleeper recovery snapshot without constructing a backend client", async () => {
    const createClient = vi.fn();
    const fetchSleeperRecovery = vi.fn(async () => ({
      status: "ready" as const,
      request: {
        source: "sleeper_api" as const,
        observed_at: "2026-08-23T00:00:00Z",
        declared_complete: true,
        picks: [],
      },
      eventIds: [],
    }));
    const response = await handleWorkerRequest(
      {
        type: "nfl_fantasy_assistant_backend",
        operation: "sleeper_recovery",
        pageUrl: "https://sleeper.com/draft/nfl/draft-fixture",
        observedAt: "2026-08-23T00:00:00Z",
      },
      {
        loadConfiguration: async () => configuration,
        createClient,
        fetchSleeperRecovery,
      },
    );
    expect(response).toMatchObject({ ok: true });
    expect(createClient).not.toHaveBeenCalled();
    expect(fetchSleeperRecovery).toHaveBeenCalledOnce();
  });

  it("returns a non-mutating validation error when Sleeper recovery is unsafe", async () => {
    const createClient = vi.fn();
    const response = await handleWorkerRequest(
      {
        type: "nfl_fantasy_assistant_backend",
        operation: "sleeper_recovery",
        pageUrl: "https://sleeper.com/draft/nfl/draft-fixture",
        observedAt: "2026-08-23T00:00:00Z",
      },
      {
        loadConfiguration: async () => configuration,
        createClient,
        fetchSleeperRecovery: async () => ({
          status: "unavailable",
          code: "invalid_pick_snapshot",
          detail: "Unsafe snapshot.",
        }),
      },
    );
    expect(response).toMatchObject({
      ok: false,
      error: { kind: "validation", retryable: false },
    });
    expect(createClient).not.toHaveBeenCalled();
  });

  it("submits a verified Sleeper initialization through the neutral league and draft endpoints", async () => {
    const calls: Array<{ url: string; body?: string }> = [];
    const client = new BackendApiClient({
      configuration,
      fetcher: async (url, init) => {
        calls.push({
          url: String(url),
          body: init?.body as string | undefined,
        });
        const path = String(url);
        if (path.endsWith("/v1/diagnostics")) {
          return new Response(
            JSON.stringify({
              api_version: "v1",
              database: { status: "ready", detail: "fixture" },
              data: { status: "ready", detail: "fixture" },
              identity: { status: "ready", detail: "fixture" },
              adapter: { status: "unavailable", detail: "fixture" },
              recommendations: { status: "ready", detail: "fixture" },
            }),
            { status: 200 },
          );
        }
        const isLeague = path.endsWith("/v1/leagues");
        return new Response(
          JSON.stringify(
            isLeague
              ? { league_id: "league-local", config_version: "fixture" }
              : {
                  draft_id: "draft-local",
                  league_id: "league-local",
                  status: "active",
                  reconciliation_state: "current",
                  revision: 0,
                  current_pick: 1,
                  dataset_version: "dataset-fixture",
                  feature_version: "feature-fixture",
                  model_version: "model-fixture",
                  accepted_picks: 0,
                  unresolved_observations: 0,
                  issues: [],
                },
          ),
          { status: 200 },
        );
      },
    });
    const response = await handleWorkerRequest(
      {
        type: "nfl_fantasy_assistant_backend",
        operation: "sleeper_initialize",
        pageUrl: "https://sleeper.com/draft/nfl/draft-fixture",
        observedAt: "2026-08-23T00:00:00Z",
      },
      {
        loadConfiguration: async () => configuration,
        createClient: () => client,
        loadSleeperInitializationConfiguration: async () => ({
          userId: "user-fixture",
          datasetVersion: "dataset-fixture",
          featureVersion: "feature-fixture",
          modelVersion: "model-fixture",
        }),
        fetchSleeperInitialization: async () => ({
          status: "ready",
          leagueRequest: {
            provider: "sleeper",
            provider_league_id: "league-fixture",
            config: {
              config_version: "fixture",
              team_count: 8,
              draft_type: "snake",
              roster_slots: [
                { name: "QB-1", eligible_positions: ["QB"], is_bench: false },
              ],
              scoring_rules: {},
            },
          },
          draftRequest: {
            league_id: "pending_backend_league_registration",
            provider: "sleeper",
            provider_draft_id: "draft-fixture",
            config: {
              config_version: "fixture",
              team_count: 8,
              draft_type: "snake",
              roster_slots: [
                { name: "QB-1", eligible_positions: ["QB"], is_bench: false },
              ],
              scoring_rules: {},
            },
            user_team_id: "roster-fixture-1",
            user_slot: 1,
            draft_order: Array.from(
              { length: 8 },
              (_, index) => `roster-fixture-${index + 1}`,
            ),
            dataset_version: "dataset-fixture",
            feature_version: "feature-fixture",
            model_version: "model-fixture",
            initial_picks: [],
          },
          recovery: {
            status: "ready",
            request: {
              source: "sleeper_api",
              observed_at: "2026-08-23T00:00:00Z",
              declared_complete: true,
              picks: [],
            },
            eventIds: [],
          },
        }),
      },
    );

    expect(response).toMatchObject({
      ok: true,
      data: { draft_id: "draft-local" },
    });
    expect(calls.map((call) => call.url)).toEqual([
      "http://127.0.0.1:8765/v1/diagnostics",
      "http://127.0.0.1:8765/v1/leagues",
      "http://127.0.0.1:8765/v1/drafts",
    ]);
    expect(calls[2].body).toContain('"league_id":"league-local"');
  });

  it("does not read Sleeper or mutate the backend until the local runtime is ready", async () => {
    const fetchSleeperInitialization = vi.fn();
    const client = new BackendApiClient({
      configuration,
      fetcher: async () =>
        new Response(
          JSON.stringify({
            api_version: "v1",
            database: { status: "ready", detail: "fixture" },
            data: { status: "unavailable", detail: "fixture" },
            identity: { status: "unavailable", detail: "fixture" },
            adapter: { status: "unavailable", detail: "fixture" },
            recommendations: { status: "unavailable", detail: "fixture" },
          }),
          { status: 200 },
        ),
    });
    const response = await handleWorkerRequest(
      {
        type: "nfl_fantasy_assistant_backend",
        operation: "sleeper_initialize",
        pageUrl: "https://sleeper.com/draft/nfl/draft-fixture",
        observedAt: "2026-08-23T00:00:00Z",
      },
      {
        loadConfiguration: async () => configuration,
        createClient: () => client,
        fetchSleeperInitialization,
      },
    );

    expect(response).toMatchObject({
      ok: false,
      error: { kind: "unavailable", retryable: false },
    });
    expect(fetchSleeperInitialization).not.toHaveBeenCalled();
  });
});
