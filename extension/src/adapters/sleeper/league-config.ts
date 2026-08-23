/** Translate a verified Sleeper league shape into the neutral initialization configuration. */

import type { components } from "../../api/generated-contract.js";

import { adaptSleeperScoringSettings } from "./scoring.js";

type LeagueConfigInput = components["schemas"]["LeagueConfigInput"];
type RosterSlotInput = components["schemas"]["RosterSlotInput"];

const SLEEPER_ROSTER_SLOTS: Readonly<
  Record<string, Omit<RosterSlotInput, "name">>
> = {
  QB: { eligible_positions: ["QB"], is_bench: false },
  RB: { eligible_positions: ["RB"], is_bench: false },
  WR: { eligible_positions: ["WR"], is_bench: false },
  TE: { eligible_positions: ["TE"], is_bench: false },
  K: { eligible_positions: ["K"], is_bench: false },
  DEF: { eligible_positions: ["DEF"], is_bench: false },
  WRRB_FLEX: { eligible_positions: ["WR", "RB"], is_bench: false },
  BN: {
    eligible_positions: ["QB", "RB", "WR", "TE", "K", "DEF"],
    is_bench: true,
  },
};

export type SleeperLeagueConfigurationResult =
  | { status: "ready"; config: LeagueConfigInput }
  | {
      status: "unavailable";
      code:
        | "invalid_league_shape"
        | "unsupported_roster_slot"
        | "unsupported_draft_type"
        | "invalid_scoring_value"
        | "unsupported_scoring_rule"
        | "duplicate_scoring_rule"
        | "conflicting_scoring_rules";
      detail: string;
    };

/**
 * This boundary intentionally accepts only fields verified from the documented league response
 * plus the independently verified draft type. It does not pass provider keys beyond this module.
 */
export function adaptSleeperLeagueConfiguration(input: {
  configVersion: string;
  draftType: unknown;
  totalRosters: unknown;
  rosterPositions: unknown;
  scoringSettings: unknown;
}): SleeperLeagueConfigurationResult {
  if (input.draftType !== "snake") {
    return {
      status: "unavailable",
      code: "unsupported_draft_type",
      detail:
        "Only a verified Sleeper snake draft can initialize this configuration.",
    };
  }
  if (
    !Number.isInteger(input.totalRosters) ||
    input.totalRosters !== 8 ||
    !Array.isArray(input.rosterPositions) ||
    !input.rosterPositions.every((position) => typeof position === "string") ||
    !input.scoringSettings ||
    typeof input.scoringSettings !== "object" ||
    Array.isArray(input.scoringSettings)
  ) {
    return {
      status: "unavailable",
      code: "invalid_league_shape",
      detail:
        "Sleeper league configuration must contain an 8-team roster list and scoring settings.",
    };
  }
  const rosterSlots: RosterSlotInput[] = [];
  const seenSlots = new Map<string, number>();
  for (const providerSlot of input.rosterPositions) {
    const slot = SLEEPER_ROSTER_SLOTS[providerSlot];
    if (!slot) {
      return {
        status: "unavailable",
        code: "unsupported_roster_slot",
        detail: "A Sleeper roster position has no verified neutral mapping.",
      };
    }
    const occurrence = (seenSlots.get(providerSlot) ?? 0) + 1;
    seenSlots.set(providerSlot, occurrence);
    rosterSlots.push({ ...slot, name: `${providerSlot}-${occurrence}` });
  }
  const scoring = adaptSleeperScoringSettings(
    input.scoringSettings as Record<string, unknown>,
  );
  if (scoring.status !== "ready") return scoring;
  return {
    status: "ready",
    config: {
      config_version: input.configVersion,
      team_count: input.totalRosters,
      draft_type: "snake",
      roster_slots: rosterSlots,
      scoring_rules: scoring.scoringRules,
    },
  };
}
