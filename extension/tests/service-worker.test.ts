import { describe, expect, it } from "vitest";

import { BackendApiClient } from "../src/api/client.js";
import { handleWorkerRequest } from "../src/service-worker.js";

const configuration = {
  baseUrl: "http://127.0.0.1:8765",
  bearerToken: "a".repeat(43),
};

describe("service-worker relay", () => {
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
});
