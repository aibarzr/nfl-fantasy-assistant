import { describe, expect, it } from "vitest";

import { detectEspnDraftSurface } from "../src/adapters/espn/surface.js";
import { validateEspnPageMessage } from "../src/content/page-messages.js";

const supportedUrl = "https://fantasy.espn.com/football/draft?discarded=query";
const pageWindow = {};

function pageEvent(
  data: unknown,
  overrides: Partial<MessageEvent<unknown>> = {},
): MessageEvent<unknown> {
  return {
    data,
    origin: "https://fantasy.espn.com",
    source: pageWindow as MessageEventSource,
    ...overrides,
  } as MessageEvent<unknown>;
}

describe("ESPN draft surface", () => {
  it("accepts only the exact confirmed host and pathname", () => {
    expect(detectEspnDraftSurface(supportedUrl)).toEqual({
      supported: true,
      surface: "espn_draft",
      leagueProvider: "espn",
    });

    for (const lookalike of [
      "https://fantasy.espn.com.evil.test/football/draft",
      "https://draft.fantasy.espn.com/football/draft",
      "https://espn.com/football/draft",
      "http://fantasy.espn.com/football/draft",
      "https://fantasy.espn.com/football/draft/",
      "https://fantasy.espn.com/football/league",
    ]) {
      expect(detectEspnDraftSurface(lookalike).supported).toBe(false);
    }
  });

  it("accepts only a bounded, known page message from the active exact-origin window", () => {
    const valid = validateEspnPageMessage(
      supportedUrl,
      pageEvent({
        type: "nfl_fantasy_assistant_espn_adapter",
        operation: "adapter_diagnostic",
        surface: "espn_draft",
        payload: { code: "adapter_ready" },
      }),
      pageWindow,
    );
    expect(valid).toMatchObject({
      valid: true,
      surface: { surface: "espn_draft" },
    });

    expect(
      validateEspnPageMessage(
        supportedUrl,
        pageEvent(
          {
            type: "nfl_fantasy_assistant_espn_adapter",
            operation: "adapter_diagnostic",
            surface: "espn_draft",
            payload: {},
          },
          { origin: "https://evil.test" },
        ),
        pageWindow,
      ),
    ).toMatchObject({ valid: false, code: "invalid_message_origin" });
    expect(
      validateEspnPageMessage(
        supportedUrl,
        pageEvent(
          {
            type: "nfl_fantasy_assistant_espn_adapter",
            operation: "adapter_diagnostic",
            surface: "espn_draft",
            payload: {},
          },
          { source: {} as MessageEventSource },
        ),
        pageWindow,
      ),
    ).toMatchObject({ valid: false, code: "invalid_message_source" });
    expect(
      validateEspnPageMessage(
        supportedUrl,
        pageEvent({
          type: "nfl_fantasy_assistant_espn_adapter",
          operation: "unknown_operation",
          surface: "espn_draft",
          payload: {},
        }),
        pageWindow,
      ),
    ).toMatchObject({ valid: false, code: "unsupported_message_operation" });
    expect(
      validateEspnPageMessage(
        supportedUrl,
        pageEvent({
          type: "nfl_fantasy_assistant_espn_adapter",
          operation: "adapter_diagnostic",
          surface: "espn_draft",
          payload: { oversized: "x".repeat(16 * 1024) },
        }),
        pageWindow,
      ),
    ).toMatchObject({ valid: false, code: "invalid_message_size" });
    expect(
      validateEspnPageMessage(
        "https://fantasy.espn.com/football/league",
        pageEvent({
          type: "nfl_fantasy_assistant_espn_adapter",
          operation: "adapter_diagnostic",
          surface: "espn_draft",
          payload: {},
        }),
        pageWindow,
      ),
    ).toMatchObject({ valid: false, code: "incompatible_surface" });
  });
});
