/** Translate a complete documented Sleeper picks response into neutral recovery facts. */

import type { components } from "../../api/generated-contract.js";

type ObservedPickInput = components["schemas"]["ObservedPickInput"];
type SnapshotRequest = components["schemas"]["SnapshotRequest"];

type SleeperPick = {
  draft_id: string;
  pick_no: number;
  draft_slot: number;
  roster_id: string;
  player_id: string;
  metadata: {
    player_id: string;
    position: string;
    team?: string;
    sport?: string;
  };
};

export type SleeperRecoveryResult =
  | { status: "ready"; request: SnapshotRequest; eventIds: string[] }
  | {
      status: "unavailable";
      code: "invalid_draft_identity" | "invalid_pick_snapshot";
      detail: string;
    };

const POSITIONS = new Set<ObservedPickInput["player"]["position"]>([
  "QB",
  "RB",
  "WR",
  "TE",
  "K",
  "DEF",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function expectedDraftSlot(pickNumber: number): number {
  const offset = (pickNumber - 1) % 8;
  return Math.floor((pickNumber - 1) / 8) % 2 === 0 ? offset + 1 : 8 - offset;
}

function asNflTeam(value: unknown): string | undefined {
  return typeof value === "string" && /^[A-Z]{2,4}$/.test(value)
    ? value
    : undefined;
}

function parsePick(
  value: unknown,
  expectedPickNumber: number,
): SleeperPick | undefined {
  if (!isRecord(value) || !isRecord(value.metadata)) return undefined;
  const metadata = value.metadata;
  if (
    !nonEmptyString(value.draft_id) ||
    !Number.isInteger(value.pick_no) ||
    value.pick_no !== expectedPickNumber ||
    !Number.isInteger(value.draft_slot) ||
    value.draft_slot !== expectedDraftSlot(expectedPickNumber) ||
    !nonEmptyString(value.roster_id) ||
    !nonEmptyString(value.player_id) ||
    !nonEmptyString(metadata.player_id) ||
    metadata.player_id !== value.player_id ||
    !nonEmptyString(metadata.position) ||
    !POSITIONS.has(
      metadata.position as ObservedPickInput["player"]["position"],
    ) ||
    (metadata.sport !== undefined && metadata.sport !== "nfl")
  ) {
    return undefined;
  }
  return {
    draft_id: value.draft_id,
    pick_no: value.pick_no,
    draft_slot: value.draft_slot,
    roster_id: value.roster_id,
    player_id: value.player_id,
    metadata: {
      player_id: metadata.player_id,
      position: metadata.position,
      team: typeof metadata.team === "string" ? metadata.team : undefined,
      sport: typeof metadata.sport === "string" ? metadata.sport : undefined,
    },
  };
}

export function sleeperPickEventId(
  draftId: string,
  pickNumber: number,
): string {
  return `sleeper:${draftId}:pick:${pickNumber}`;
}

export function adaptSleeperRecoverySnapshot(
  draftId: string,
  picks: unknown,
  observedAt: string,
  slotToRosterId?: Record<string, string>,
): SleeperRecoveryResult {
  if (!nonEmptyString(draftId) || !Array.isArray(picks) || picks.length > 256) {
    return {
      status: "unavailable",
      code: "invalid_pick_snapshot",
      detail: "Sleeper picks are not a bounded complete 8-team draft snapshot.",
    };
  }
  const parsedPicks = picks.map((pick, index) => parsePick(pick, index + 1));
  if (parsedPicks.some((pick) => pick === undefined)) {
    return {
      status: "unavailable",
      code: "invalid_pick_snapshot",
      detail:
        "Sleeper picks must be a complete contiguous 8-team snake snapshot.",
    };
  }
  const verifiedPicks = parsedPicks as SleeperPick[];
  if (verifiedPicks.some((pick) => pick.draft_id !== draftId)) {
    return {
      status: "unavailable",
      code: "invalid_draft_identity",
      detail:
        "The documented picks response does not match the active Sleeper draft.",
    };
  }
  if (
    slotToRosterId &&
    verifiedPicks.some(
      (pick) => slotToRosterId[String(pick.draft_slot)] !== pick.roster_id,
    )
  ) {
    return {
      status: "unavailable",
      code: "invalid_draft_identity",
      detail:
        "Sleeper picks do not match the validated draft slot-to-roster mapping.",
    };
  }
  return {
    status: "ready",
    request: {
      source: "sleeper_api",
      observed_at: observedAt,
      declared_complete: true,
      picks: verifiedPicks.map((pick) => ({
        overall_pick: pick.pick_no,
        team_id: pick.roster_id,
        player: {
          provider: "sleeper",
          external_id: pick.player_id,
          position: pick.metadata
            .position as ObservedPickInput["player"]["position"],
          nfl_team: asNflTeam(pick.metadata.team),
        },
      })),
    },
    eventIds: verifiedPicks.map((pick) =>
      sleeperPickEventId(draftId, pick.pick_no),
    ),
  };
}
