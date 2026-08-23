import { describe, expect, it } from "vitest";

import {
  SLEEPER_SCORING_CODEBOOK_VERSION,
  adaptSleeperScoringSettings,
} from "../src/adapters/sleeper/scoring.js";

describe("Sleeper scoring adapter", () => {
  it("maps observed K/DEF bands to neutral scoring semantics", () => {
    expect(
      adaptSleeperScoringSettings({
        pass_td: 6,
        rec: 1,
        fgm_0_19: 3,
        fgm_50p: 5,
        fgmiss_30_39: -1,
        xpm: 1,
        xpmiss: -1.5,
        def_sack: 1,
        def_int: 2,
        def_fr: 2,
        def_td: 6,
        def_safe: 2,
        pts_allow_0: 10,
        pts_allow_35p: -4,
      }),
    ).toEqual({
      status: "ready",
      codebookVersion: SLEEPER_SCORING_CODEBOOK_VERSION,
      scoringRules: {
        passing_touchdowns: 6,
        receptions: 1,
        field_goals_made_0_19: 3,
        field_goals_made_50_plus: 5,
        field_goals_missed_30_39: -1,
        extra_points_made: 1,
        extra_points_missed: -1.5,
        defensive_sacks: 1,
        defensive_interceptions: 2,
        defensive_fumble_recoveries: 2,
        defensive_touchdowns: 6,
        defensive_safeties: 2,
        defensive_points_allowed_0: 10,
        defensive_points_allowed_35_plus: -4,
      },
    });
  });

  it("fails closed for unknown, invalid, or colliding enabled rules", () => {
    expect(adaptSleeperScoringSettings({ unknown_rule: 1 })).toMatchObject({
      status: "unavailable",
      code: "unsupported_scoring_rule",
    });
    expect(adaptSleeperScoringSettings({ pass_td: "6" })).toMatchObject({
      status: "unavailable",
      code: "invalid_scoring_value",
    });
    expect(adaptSleeperScoringSettings({ fgm: 3, fgm_50p: 5 })).toMatchObject({
      status: "unavailable",
      code: "conflicting_scoring_rules",
    });
  });
});
