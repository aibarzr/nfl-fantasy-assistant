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
});
