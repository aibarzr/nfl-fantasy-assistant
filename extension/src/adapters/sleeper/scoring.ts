/** Translate verified Sleeper scoring keys into the neutral semantic codebook. */

import type { components } from "../../api/generated-contract.js";

type LeagueConfigInput = components["schemas"]["LeagueConfigInput"];

export const SLEEPER_SCORING_CODEBOOK_VERSION = "sleeper-semantic-v3";

const RULES: Readonly<Record<string, string>> = {
  pass_yd: "passing_yards",
  pass_td: "passing_touchdowns",
  pass_int: "interceptions",
  rush_yd: "rushing_yards",
  rush_td: "rushing_touchdowns",
  rec: "receptions",
  rec_yd: "receiving_yards",
  rec_td: "receiving_touchdowns",
  fum_lost: "fumbles_lost",
  fgm: "field_goals_made",
  fgm_0_19: "field_goals_made_0_19",
  fgm_20_29: "field_goals_made_20_29",
  fgm_30_39: "field_goals_made_30_39",
  fgm_40_49: "field_goals_made_40_49",
  fgm_50p: "field_goals_made_50_plus",
  fgmiss: "field_goals_missed",
  fgmiss_0_19: "field_goals_missed_0_19",
  fgmiss_20_29: "field_goals_missed_20_29",
  fgmiss_30_39: "field_goals_missed_30_39",
  fgmiss_40_49: "field_goals_missed_40_49",
  fgmiss_50p: "field_goals_missed_50_plus",
  xpm: "extra_points_made",
  xpmiss: "extra_points_missed",
  sack: "defensive_sacks",
  int: "defensive_interceptions",
  fum_rec: "defensive_fumble_recoveries",
  // The observed non-IDP league awards this D/ST event in place of a generic DEF-TD key.
  fum_rec_td: "defensive_touchdowns",
  safe: "defensive_safeties",
  pts_allow: "points_allowed",
  yards_allow: "yards_allowed",
  pts_allow_0: "defensive_points_allowed_0",
  pts_allow_1_6: "defensive_points_allowed_1_6",
  pts_allow_7_13: "defensive_points_allowed_7_13",
  pts_allow_14_20: "defensive_points_allowed_14_20",
  pts_allow_21_27: "defensive_points_allowed_21_27",
  pts_allow_28_34: "defensive_points_allowed_28_34",
  pts_allow_35p: "defensive_points_allowed_35_plus",
};

const MUTUALLY_EXCLUSIVE_RULES = [
  [
    "field_goals_made",
    "field_goals_made_0_19",
    "field_goals_made_20_29",
    "field_goals_made_30_39",
    "field_goals_made_40_49",
    "field_goals_made_50_plus",
  ],
  [
    "field_goals_missed",
    "field_goals_missed_0_19",
    "field_goals_missed_20_29",
    "field_goals_missed_30_39",
    "field_goals_missed_40_49",
    "field_goals_missed_50_plus",
  ],
  [
    "points_allowed",
    "defensive_points_allowed_0",
    "defensive_points_allowed_1_6",
    "defensive_points_allowed_7_13",
    "defensive_points_allowed_14_20",
    "defensive_points_allowed_21_27",
    "defensive_points_allowed_28_34",
    "defensive_points_allowed_35_plus",
  ],
] as const;

export type SleeperScoringResult =
  | {
      status: "ready";
      codebookVersion: typeof SLEEPER_SCORING_CODEBOOK_VERSION;
      scoringRules: LeagueConfigInput["scoring_rules"];
    }
  | {
      status: "unavailable";
      code:
        | "invalid_scoring_value"
        | "unsupported_scoring_rule"
        | "duplicate_scoring_rule"
        | "conflicting_scoring_rules";
      detail: string;
    };

/**
 * Disabled provider settings are intentionally ignored. Every enabled setting must map one-to-one
 * to a neutral semantic key; this avoids accepting an approximation under a familiar rule name.
 */
export function adaptSleeperScoringSettings(
  settings: Record<string, unknown>,
): SleeperScoringResult {
  const scoringRules: Record<string, number> = {};
  for (const [providerRule, rawValue] of Object.entries(settings).sort(
    ([left], [right]) => left.localeCompare(right),
  )) {
    if (typeof rawValue !== "number" || !Number.isFinite(rawValue)) {
      return {
        status: "unavailable",
        code: "invalid_scoring_value",
        detail: "Sleeper scoring settings must contain finite numeric values.",
      };
    }
    if (rawValue === 0) continue;
    const semanticRule = RULES[providerRule];
    if (!semanticRule) {
      return {
        status: "unavailable",
        code: "unsupported_scoring_rule",
        detail:
          "An enabled Sleeper scoring rule has no verified neutral semantic mapping.",
      };
    }
    if (semanticRule in scoringRules) {
      return {
        status: "unavailable",
        code: "duplicate_scoring_rule",
        detail:
          "Multiple enabled Sleeper scoring rules map to one neutral semantic rule.",
      };
    }
    scoringRules[semanticRule] = rawValue;
  }
  if (
    MUTUALLY_EXCLUSIVE_RULES.some(
      ([flatRule, ...bandRules]) =>
        flatRule in scoringRules &&
        bandRules.some((rule) => rule in scoringRules),
    )
  ) {
    return {
      status: "unavailable",
      code: "conflicting_scoring_rules",
      detail:
        "Sleeper flat and banded scoring rules cannot both map to one neutral configuration.",
    };
  }
  return {
    status: "ready",
    codebookVersion: SLEEPER_SCORING_CODEBOOK_VERSION,
    scoringRules,
  };
}
