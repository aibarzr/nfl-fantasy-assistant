import { describe, expect, it, vi } from "vitest";

import { BackendApiClient } from "../src/api/client.js";

const configuration = {
  baseUrl: "http://127.0.0.1:8765",
  bearerToken: "a".repeat(43),
};

function jsonResponse(body: object, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("backend API client", () => {
  it("uses bearer authentication, a correlation ID, and the checked health response", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ status: "ok", api_version: "v1" }));
    const client = new BackendApiClient({ configuration, fetcher });

    await expect(client.health()).resolves.toEqual({
      status: "ok",
      api_version: "v1",
    });
    const [, init] = fetcher.mock.calls[0] ?? [];
    expect(init?.credentials).toBe("omit");
    expect(init?.headers).toMatchObject({
      Authorization: `Bearer ${configuration.bearerToken}`,
      "Content-Type": "application/json",
    });
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.["X-Request-ID"]).toMatch(/^ext_/);
  });

  it("retries only safe event submission after an unavailable backend", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValueOnce(
        jsonResponse({
          outcome: "accepted",
          revision: 1,
          replayed: false,
          draft: {},
        }),
      );
    const client = new BackendApiClient({ configuration, fetcher });

    await client.ingestEvent("draft/one", {
      event_id: "event-1",
      observed_at: "2026-08-01T12:00:00Z",
      surface: "espn",
      league_provider: "espn",
      type: "player_drafted",
      pick: {
        overall_pick: 1,
        team_id: "team-1",
        player: { provider: "espn", external_id: "1" },
      },
    });

    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher.mock.calls[0]?.[0]).toContain("draft%2Fone/events");
  });

  it("classifies unauthorized, unavailable, and incompatible responses without exposing a token", async () => {
    const unauthorized = new BackendApiClient({
      configuration,
      fetcher: vi.fn<typeof fetch>().mockResolvedValue(
        jsonResponse(
          {
            error: {
              message: "Valid bearer authentication is required.",
              retryable: false,
            },
          },
          401,
        ),
      ),
    });
    await expect(unauthorized.diagnostics()).rejects.toMatchObject({
      kind: "authentication",
      retryable: false,
    });

    const incompatible = new BackendApiClient({
      configuration,
      fetcher: vi
        .fn<typeof fetch>()
        .mockResolvedValue(jsonResponse({ status: "ok", api_version: "v2" })),
    });
    await expect(incompatible.health()).rejects.toMatchObject({
      kind: "incompatible",
      retryable: false,
    });
  });
});
