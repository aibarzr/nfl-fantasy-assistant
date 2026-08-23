import fixture from "../../docs/sleeper-data/sleeper-8-team-recovery-snapshot.json" with {
  type: "json",
};
import { describe, expect, it } from "vitest";

import { adaptSleeperInitializationSnapshot } from "../src/adapters/sleeper/initial-snapshot.js";
import { fetchSleeperInitializationSnapshot } from "../src/adapters/sleeper/api.js";

const context = {
  userId: "user-fixture",
  datasetVersion: "dataset-fixture",
  featureVersion: "feature-fixture",
  modelVersion: "model-fixture",
};

const observedScoring = {
  pass_td: 6,
  pass_int: -2,
  rush_td: 6,
  rec: 1,
  rec_td: 6,
  fum_lost: -2,
  fgm_0_19: 3,
  fgm_20_29: 3,
  fgm_30_39: 3,
  fgm_40_49: 3,
  fgm_50p: 5,
  fgmiss_0_19: -1,
  fgmiss_20_29: -1,
  fgmiss_30_39: -1,
  xpm: 1,
  xpmiss: -1.5,
  sack: 1,
  int: 2,
  fum_rec: 2,
  fum_rec_td: 6,
  safe: 2,
  pts_allow_0: 10,
  pts_allow_1_6: 7,
  pts_allow_7_13: 4,
  pts_allow_14_20: 1,
  pts_allow_21_27: 0,
  pts_allow_28_34: -1,
  pts_allow_35p: -4,
};

function input(overrides: Record<string, unknown> = {}) {
  return {
    draftId: fixture.draft.draft_id,
    draft: fixture.draft,
    league: {
      league_id: fixture.draft.league_id,
      draft_id: fixture.draft.draft_id,
      sport: "nfl",
      total_rosters: 8,
      roster_positions: [
        "QB",
        "RB",
        "RB",
        "WR",
        "WR",
        "TE",
        "WRRB_FLEX",
        "K",
        "DEF",
        "BN",
      ],
      scoring_settings: observedScoring,
    },
    users: [{ user_id: context.userId }],
    rosters: Array.from({ length: 8 }, (_, index) => ({
      league_id: fixture.draft.league_id,
      roster_id: `roster-fixture-${index + 1}`,
      owner_id: index === 6 ? context.userId : `other-user-${index + 1}`,
    })),
    picks: fixture.picks,
    observedAt: "2026-08-23T00:00:00Z",
    context,
    ...overrides,
  };
}

describe("Sleeper initialization adapter", () => {
  it("builds neutral league and snake-draft requests from same-scoped API facts", () => {
    const result = adaptSleeperInitializationSnapshot(input());

    expect(result).toMatchObject({ status: "ready" });
    if (result.status !== "ready")
      throw new Error("expected a ready initialization");
    expect(result.leagueRequest).toMatchObject({
      provider: "sleeper",
      provider_league_id: "league-fixture",
      config: { config_version: "sleeper-semantic-v3", team_count: 8 },
    });
    expect(result.draftRequest).toMatchObject({
      provider: "sleeper",
      provider_draft_id: "draft-fixture",
      user_team_id: "roster-fixture-7",
      user_slot: 7,
      dataset_version: "dataset-fixture",
    });
    expect(result.draftRequest.initial_picks).toHaveLength(
      fixture.picks.length,
    );
    expect(result.draftRequest.draft_order).toHaveLength(104);
    expect(result.draftRequest.draft_order.slice(0, 9)).toEqual([
      "roster-fixture-1",
      "roster-fixture-2",
      "roster-fixture-3",
      "roster-fixture-4",
      "roster-fixture-5",
      "roster-fixture-6",
      "roster-fixture-7",
      "roster-fixture-8",
      "roster-fixture-8",
    ]);
    expect(JSON.stringify(result)).not.toContain("pass_td");
  });

  it("rejects a user that cannot be proved to own exactly one same-league roster", () => {
    const base = input();
    const result = adaptSleeperInitializationSnapshot({
      ...base,
      rosters: base.rosters.slice(0, 7),
    });
    expect(result).toMatchObject({
      status: "unavailable",
      code: "user_slot_unavailable",
    });
  });

  it("rejects a user-to-slot declaration that conflicts with roster evidence", () => {
    const result = adaptSleeperInitializationSnapshot(
      input({
        draft: {
          ...fixture.draft,
          draft_order: { [context.userId]: 1 },
        },
      }),
    );
    expect(result).toMatchObject({
      status: "unavailable",
      code: "user_slot_unavailable",
    });
  });

  it("rejects a cross-scoped league before accepting a configuration", () => {
    const base = input();
    const result = adaptSleeperInitializationSnapshot({
      ...base,
      league: { ...base.league, draft_id: "other-draft" },
    });
    expect(result).toMatchObject({
      status: "unavailable",
      code: "invalid_league_identity",
    });
  });

  it("reads only the documented initialization endpoints after exact-surface activation", async () => {
    const base = input();
    const requested: string[] = [];
    const fetcher = async (url: string | URL) => {
      const target = String(url);
      requested.push(target);
      const payload = target.endsWith("/rosters")
        ? base.rosters
        : target.endsWith("/users")
          ? base.users
          : target.endsWith("/picks")
            ? base.picks
            : target.includes("/league/")
              ? base.league
              : base.draft;
      return new Response(JSON.stringify(payload), { status: 200 });
    };

    await expect(
      fetchSleeperInitializationSnapshot(
        "https://sleeper.com/draft/nfl/draft-fixture",
        base.observedAt,
        context,
        fetcher as typeof fetch,
      ),
    ).resolves.toMatchObject({ status: "ready" });
    expect(requested).toEqual([
      "https://api.sleeper.app/v1/draft/draft-fixture",
      "https://api.sleeper.app/v1/league/league-fixture",
      "https://api.sleeper.app/v1/league/league-fixture/rosters",
      "https://api.sleeper.app/v1/league/league-fixture/users",
      "https://api.sleeper.app/v1/draft/draft-fixture/picks",
    ]);
  });
});
