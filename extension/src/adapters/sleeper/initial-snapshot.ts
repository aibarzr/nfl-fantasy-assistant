/** Convert documented Sleeper API facts into one neutral, fail-closed initialization request. */

import type { components } from "../../api/generated-contract.js";
import type { SleeperInitializationConfiguration } from "../../config/sleeper-initialization.js";

import { adaptSleeperLeagueConfiguration } from "./league-config.js";
import {
  adaptSleeperRecoverySnapshot,
  type SleeperRecoveryResult,
} from "./recovery-snapshot.js";
import { SLEEPER_SCORING_CODEBOOK_VERSION } from "./scoring.js";

type DraftCreateRequest = components["schemas"]["DraftCreateRequest"];
type LeagueCreateRequest = components["schemas"]["LeagueCreateRequest"];

export const SLEEPER_CONFIG_CODEBOOK_VERSION = SLEEPER_SCORING_CODEBOOK_VERSION;

export type SleeperInitializationResult =
  | {
      status: "ready";
      leagueRequest: LeagueCreateRequest;
      draftRequest: DraftCreateRequest;
      recovery: Extract<SleeperRecoveryResult, { status: "ready" }>;
    }
  | {
      status: "unavailable";
      code:
        | "invalid_draft_identity"
        | "invalid_league_identity"
        | "invalid_draft_order"
        | "user_slot_unavailable"
        | "invalid_pick_snapshot"
        | "invalid_league_shape"
        | "unsupported_roster_slot"
        | "unsupported_draft_type"
        | "invalid_scoring_value"
        | "unsupported_scoring_rule"
        | "duplicate_scoring_rule"
        | "conflicting_scoring_rules";
      detail: string;
    };

type SleeperDraftFacts = {
  draft_id?: unknown;
  league_id?: unknown;
  type?: unknown;
  status?: unknown;
  sport?: unknown;
  settings?: { teams?: unknown; rounds?: unknown };
  slot_to_roster_id?: unknown;
  draft_order?: unknown;
};

type SleeperLeagueFacts = {
  league_id?: unknown;
  draft_id?: unknown;
  sport?: unknown;
  total_rosters?: unknown;
  roster_positions?: unknown;
  scoring_settings?: unknown;
};

function unavailable(
  code: Exclude<SleeperInitializationResult, { status: "ready" }>["code"],
  detail: string,
): SleeperInitializationResult {
  return { status: "unavailable", code, detail };
}

function opaqueId(value: unknown): string | undefined {
  if (
    (typeof value !== "string" && typeof value !== "number") ||
    `${value}`.trim().length === 0
  ) {
    return undefined;
  }
  return `${value}`;
}

function record(value: unknown): Record<string, unknown> | undefined {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function slots(value: unknown): Record<string, string> | undefined {
  const raw = record(value);
  if (!raw || Object.keys(raw).length !== 8) return undefined;
  const result: Record<string, string> = {};
  for (let slot = 1; slot <= 8; slot += 1) {
    const rosterId = opaqueId(raw[String(slot)]);
    if (!rosterId) return undefined;
    result[String(slot)] = rosterId;
  }
  return new Set(Object.values(result)).size === 8 ? result : undefined;
}

function expectedSlot(pickNumber: number): number {
  const offset = (pickNumber - 1) % 8;
  return Math.floor((pickNumber - 1) / 8) % 2 === 0 ? offset + 1 : 8 - offset;
}

function draftOrder(
  slotToRosterId: Record<string, string>,
  rounds: number,
): string[] {
  return Array.from(
    { length: rounds * 8 },
    (_, index) => slotToRosterId[String(expectedSlot(index + 1))],
  );
}

function hasMatchingDeclaredSlot(
  value: unknown,
  userId: string,
  slot: number,
): boolean {
  if (value === undefined || value === null) return true;
  const order = record(value);
  if (!order || Object.keys(order).length === 0) return true;
  return order[userId] === slot;
}

function userRosterAndSlot(
  users: unknown,
  rosters: unknown,
  leagueId: string,
  userId: string,
  slotToRosterId: Record<string, string>,
): { rosterId: string; slot: number } | undefined {
  if (
    !Array.isArray(users) ||
    !Array.isArray(rosters) ||
    rosters.length !== 8
  ) {
    return undefined;
  }
  const matchingUsers = users.filter(
    (user) => record(user)?.user_id === userId,
  );
  if (matchingUsers.length !== 1) return undefined;
  const normalizedRosters = rosters.map((roster) => {
    const value = record(roster);
    return {
      rosterId: opaqueId(value?.roster_id),
      ownerId: opaqueId(value?.owner_id),
      leagueId: opaqueId(value?.league_id),
    };
  });
  if (
    normalizedRosters.some(
      (roster) => !roster.rosterId || roster.leagueId !== leagueId,
    ) ||
    new Set(normalizedRosters.map((roster) => roster.rosterId)).size !== 8
  ) {
    return undefined;
  }
  const owned = normalizedRosters.filter((roster) => roster.ownerId === userId);
  if (owned.length !== 1 || !owned[0].rosterId) return undefined;
  const slot = Object.entries(slotToRosterId).find(
    ([, rosterId]) => rosterId === owned[0].rosterId,
  )?.[0];
  return slot ? { rosterId: owned[0].rosterId, slot: Number(slot) } : undefined;
}

export function adaptSleeperInitializationSnapshot(input: {
  draftId: string;
  draft: SleeperDraftFacts;
  league: SleeperLeagueFacts;
  users: unknown;
  rosters: unknown;
  picks: unknown;
  observedAt: string;
  context: SleeperInitializationConfiguration;
}): SleeperInitializationResult {
  const draftId = opaqueId(input.draft.draft_id);
  const leagueId = opaqueId(input.draft.league_id);
  const slotToRosterId = slots(input.draft.slot_to_roster_id);
  const rounds = input.draft.settings?.rounds;
  if (
    draftId !== input.draftId ||
    !leagueId ||
    input.draft.type !== "snake" ||
    (input.draft.status !== "pre_draft" && input.draft.status !== "drafting") ||
    input.draft.sport !== "nfl" ||
    input.draft.settings?.teams !== 8 ||
    !Number.isInteger(rounds) ||
    (rounds as number) < 1 ||
    (rounds as number) > 32 ||
    !slotToRosterId
  ) {
    return unavailable(
      "invalid_draft_identity",
      "Sleeper draft metadata is not a complete supported 8-team NFL snake draft.",
    );
  }
  if (
    opaqueId(input.league.league_id) !== leagueId ||
    opaqueId(input.league.draft_id) !== input.draftId ||
    input.league.sport !== "nfl"
  ) {
    return unavailable(
      "invalid_league_identity",
      "Sleeper league metadata does not match the active draft.",
    );
  }
  const configuration = adaptSleeperLeagueConfiguration({
    configVersion: SLEEPER_CONFIG_CODEBOOK_VERSION,
    draftType: input.draft.type,
    totalRosters: input.league.total_rosters,
    rosterPositions: input.league.roster_positions,
    scoringSettings: input.league.scoring_settings,
  });
  if (configuration.status !== "ready") return configuration;
  const identity = userRosterAndSlot(
    input.users,
    input.rosters,
    leagueId,
    input.context.userId,
    slotToRosterId,
  );
  if (
    !identity ||
    !hasMatchingDeclaredSlot(
      input.draft.draft_order,
      input.context.userId,
      identity.slot,
    )
  ) {
    return unavailable(
      "user_slot_unavailable",
      "The configured Sleeper user does not resolve to one matching league roster and draft slot.",
    );
  }
  const order = draftOrder(slotToRosterId, rounds as number);
  const recovery = adaptSleeperRecoverySnapshot(
    input.draftId,
    input.picks,
    input.observedAt,
    slotToRosterId,
  );
  if (recovery.status !== "ready") return recovery;
  if (recovery.request.picks.length > order.length) {
    return unavailable(
      "invalid_pick_snapshot",
      "Sleeper picks exceed the configured draft rounds.",
    );
  }
  return {
    status: "ready",
    leagueRequest: {
      provider: "sleeper",
      provider_league_id: leagueId,
      config: configuration.config,
    },
    draftRequest: {
      league_id: "pending_backend_league_registration",
      provider: "sleeper",
      provider_draft_id: input.draftId,
      config: configuration.config,
      user_team_id: identity.rosterId,
      user_slot: identity.slot,
      draft_order: order,
      dataset_version: input.context.datasetVersion,
      feature_version: input.context.featureVersion,
      model_version: input.context.modelVersion,
      initial_picks: recovery.request.picks,
    },
    recovery,
  };
}
