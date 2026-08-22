import fixture from "../../docs/espn-data/espn-8-team-initial-snapshot.json" with {
  type: "json",
};
import { describe, expect, it } from "vitest";

import { adaptEspnInitialSnapshot } from "../src/adapters/espn/initial-snapshot.js";
import type { components } from "../src/api/generated-contract.js";

const semanticConfiguration = {
  config_version: "espn-codebook-v1",
  team_count: 8,
  draft_type: "snake",
  roster_slots: [{ name: "BN", eligible_positions: ["QB"], is_bench: true }],
  scoring_rules: {},
} satisfies components["schemas"]["LeagueConfigInput"];

const readyContext = {
  source: "structured" as const,
  providerLeagueId: "league-fixture",
  providerDraftId: "draft-fixture",
  datasetVersion: "dataset-v1",
  featureVersion: "features-v1",
  modelVersion: "model-v1",
  userIdentity: { userTeamId: "team-1", userSlot: 1 },
  leagueSemantics: {
    codebookVersion: "espn-codebook-v1",
    config: semanticConfiguration,
  },
};

describe("ESPN initial snapshot adapter", () => {
  it("keeps the captured configuration/order scope explicit and refuses its unobserved user slot", () => {
    const result = adaptEspnInitialSnapshot(fixture.snapshot, {
      source: "structured",
    });

    expect(result).toMatchObject({
      status: "unavailable",
      code: "user_slot_unavailable",
      evidence: {
        scope: "configuration_and_scheduled_order",
        declaredComplete: false,
        teamCount: 8,
      },
    });
  });

  it("serializes the checked neutral contract only when verified semantic and user context is supplied", () => {
    const result = adaptEspnInitialSnapshot(fixture.snapshot, readyContext);

    expect(result).toMatchObject({
      status: "ready",
      request: {
        provider: "espn",
        league_id: "league-fixture",
        user_team_id: "team-1",
        user_slot: 1,
        config: semanticConfiguration,
        initial_picks: [],
      },
    });
    if (result.status === "ready") {
      expect(result.request.draft_order).toHaveLength(128);
    }
  });

  it("rejects unsupported, malformed, browser-state, and DOM sources without trusted submission", () => {
    expect(
      adaptEspnInitialSnapshot(
        { ...fixture.snapshot, team_count: 10 },
        { source: "structured" },
      ),
    ).toMatchObject({ status: "unavailable", code: "unsupported_team_count" });
    expect(
      adaptEspnInitialSnapshot(
        {
          ...fixture.snapshot,
          draft: { ...fixture.snapshot.draft, scheduled_pick_order: [] },
        },
        { source: "structured" },
      ),
    ).toMatchObject({ status: "unavailable", code: "invalid_draft_order" });
    expect(
      adaptEspnInitialSnapshot(fixture.snapshot, { source: "browser_state" }),
    ).toMatchObject({
      status: "unavailable",
      code: "unobserved_source",
    });
    expect(
      adaptEspnInitialSnapshot(fixture.snapshot, { source: "dom" }),
    ).toMatchObject({
      status: "unavailable",
      code: "unobserved_source",
    });
  });

  it("rejects incomplete or contradictory verified context before creating a neutral request", () => {
    const { userIdentity: _identity, ...withoutIdentity } = readyContext;
    expect(
      adaptEspnInitialSnapshot(fixture.snapshot, withoutIdentity),
    ).toMatchObject({ status: "unavailable", code: "user_slot_unavailable" });

    const { leagueSemantics: _semantics, ...withoutCodebook } = readyContext;
    expect(
      adaptEspnInitialSnapshot(fixture.snapshot, withoutCodebook),
    ).toMatchObject({
      status: "unavailable",
      code: "configuration_codebook_unavailable",
    });

    expect(
      adaptEspnInitialSnapshot(fixture.snapshot, {
        ...readyContext,
        userIdentity: { userTeamId: "team-2", userSlot: 1 },
      }),
    ).toMatchObject({
      status: "unavailable",
      code: "initialization_context_unavailable",
    });
    expect(
      adaptEspnInitialSnapshot(fixture.snapshot, {
        ...readyContext,
        leagueSemantics: {
          ...readyContext.leagueSemantics,
          config: { ...semanticConfiguration, draft_type: "auction" },
        },
      }),
    ).toMatchObject({
      status: "unavailable",
      code: "initialization_context_unavailable",
    });
  });
});
