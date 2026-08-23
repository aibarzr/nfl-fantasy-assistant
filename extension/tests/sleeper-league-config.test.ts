import { describe, expect, it } from "vitest";

import { adaptSleeperLeagueConfiguration } from "../src/adapters/sleeper/league-config.js";

const observedScoringFixture = {
  pass_td: 6,
  pass_int: -2,
  rush_td: 6,
  rec: 1,
  rec_td: 6,
  fumble_lost: -2,
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
  def_sack: 1,
  def_int: 2,
  def_fr: 2,
  def_td: 6,
  def_safe: 2,
  pts_allow_0: 10,
  pts_allow_1_6: 7,
  pts_allow_7_13: 4,
  pts_allow_14_20: 1,
  pts_allow_21_27: 0,
  pts_allow_28_34: -1,
  pts_allow_35p: -4,
};

describe("Sleeper league configuration adapter", () => {
  it("translates the approved eight-team synthetic configuration without provider keys", () => {
    const result = adaptSleeperLeagueConfiguration({
      configVersion: "sleeper-semantic-v3-fixture",
      draftType: "snake",
      totalRosters: 8,
      rosterPositions: [
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
        "BN",
        "BN",
        "BN",
      ],
      scoringSettings: observedScoringFixture,
    });
    expect(result).toMatchObject({
      status: "ready",
      config: {
        config_version: "sleeper-semantic-v3-fixture",
        team_count: 8,
        draft_type: "snake",
        scoring_rules: {
          field_goals_made_50_plus: 5,
          field_goals_missed_30_39: -1,
          defensive_points_allowed_35_plus: -4,
        },
      },
    });
    if (result.status !== "ready")
      throw new Error("expected a ready configuration");
    expect(result.config.roster_slots).toEqual(
      expect.arrayContaining([
        { name: "QB-1", eligible_positions: ["QB"], is_bench: false },
        { name: "RB-1", eligible_positions: ["RB"], is_bench: false },
        { name: "RB-2", eligible_positions: ["RB"], is_bench: false },
        {
          name: "WRRB_FLEX-1",
          eligible_positions: ["WR", "RB"],
          is_bench: false,
        },
        { name: "K-1", eligible_positions: ["K"], is_bench: false },
        { name: "DEF-1", eligible_positions: ["DEF"], is_bench: false },
      ]),
    );
    expect(JSON.stringify(result)).not.toContain("fgm_50p");
    expect(JSON.stringify(result)).not.toContain("pts_allow_35p");
  });

  it("fails closed for unsupported roster configuration", () => {
    expect(
      adaptSleeperLeagueConfiguration({
        configVersion: "fixture",
        draftType: "snake",
        totalRosters: 8,
        rosterPositions: ["SUPER_FLEX"],
        scoringSettings: observedScoringFixture,
      }),
    ).toMatchObject({ status: "unavailable", code: "unsupported_roster_slot" });
  });
});
