import { describe, expect, it } from "vitest";

import { panelMarkup, stateFromApiError } from "../src/ui/panel.js";

describe("recommendation status presentation", () => {
  it("never maps a disconnected, unauthorized, incompatible, or conflict response to current", () => {
    expect(
      stateFromApiError({
        kind: "unavailable",
        message: "offline",
        retryable: true,
      }),
    ).toMatchObject({ kind: "disconnected", retryable: true });
    expect(
      stateFromApiError({
        kind: "authentication",
        message: "pair",
        retryable: false,
      }),
    ).toMatchObject({ kind: "unauthorized" });
    expect(
      stateFromApiError({
        kind: "incompatible",
        message: "update",
        retryable: false,
      }),
    ).toMatchObject({ kind: "incompatible" });
    expect(
      stateFromApiError({
        kind: "conflict",
        message: "reconcile",
        retryable: false,
      }),
    ).toMatchObject({ kind: "blocked" });
  });

  it("renders measured components, provenance, warnings, and long content without pick controls", () => {
    const longWarning = "Long freshness warning ".repeat(30);
    const markup = panelMarkup({
      kind: "current",
      recommendation: {
        status: "current",
        draft_id: "draft-1",
        revision: 3,
        generated_at: "2026-08-01T12:00:00Z",
        dataset_version: "dataset-v1",
        feature_version: "features-v1",
        model_version: "model-v1",
        source_updated_at: {},
        candidates: [
          {
            internal_player_id: "player-<safe>",
            rank: 1,
            draft_score: 10.5,
            confidence: 0.8,
            components: { vor: 0.9, urgency: 0.5 },
            reason_codes: ["vor_advantage"],
            reason_text: "Measured VOR advantage.",
            warnings: [longWarning],
          },
        ],
      },
    });

    expect(markup).toContain('aria-live="polite"');
    expect(markup).toContain("VOR");
    expect(markup).toContain("model-v1");
    expect(markup).toContain(longWarning);
    expect(markup).toContain("overflow-wrap: anywhere");
    expect(markup).toContain("player-&lt;safe&gt;");
    expect(markup).not.toContain("<button");
  });

  it.each([
    ["loading", "Updating draft board", "loading"],
    ["empty", "No recommendation yet", "empty"],
    ["stale", "Recommendations stale", "stale"],
    ["blocked", "Recommendations paused", "blocked"],
    ["error", "Recommendation error", "error"],
  ] as const)(
    "renders the %s state as visibly non-current",
    (kind, title, dataState) => {
      const state =
        kind === "loading" ||
        kind === "empty" ||
        kind === "stale" ||
        kind === "blocked"
          ? { kind, detail: "State details." }
          : { kind, detail: "State details.", retryable: false };

      const markup = panelMarkup(state);

      expect(markup).toContain(`data-state="${dataState}"`);
      expect(markup).toContain(title);
      expect(markup).toContain('role="status"');
      expect(markup).not.toContain('data-state="current"');
    },
  );
});
