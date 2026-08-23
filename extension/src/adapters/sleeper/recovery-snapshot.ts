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
  metadata: { position?: string; team?: string };
};

export type SleeperRecoveryResult =
  | { status: "ready"; request: SnapshotRequest; eventIds: string[] }
  | {
      status: "unavailable";
      code: "invalid_draft_identity" | "invalid_pick_snapshot";
      detail: string;
    };

function asPosition(
  value: string | undefined,
): ObservedPickInput["player"]["position"] {
  return value && ["QB", "RB", "WR", "TE", "K", "DEF"].includes(value)
    ? (value as ObservedPickInput["player"]["position"])
    : undefined;
}

export function sleeperPickEventId(
  draftId: string,
  pickNumber: number,
): string {
  return `sleeper:${draftId}:pick:${pickNumber}`;
}

export function adaptSleeperRecoverySnapshot(
  draftId: string,
  picks: SleeperPick[],
  observedAt: string,
): SleeperRecoveryResult {
  if (!draftId || picks.some((pick) => pick.draft_id !== draftId)) {
    return {
      status: "unavailable",
      code: "invalid_draft_identity",
      detail:
        "The documented picks response does not match the active Sleeper draft.",
    };
  }
  if (
    picks.length > 256 ||
    picks.some(
      (pick, index) =>
        !Number.isInteger(pick.pick_no) ||
        pick.pick_no !== index + 1 ||
        !Number.isInteger(pick.draft_slot) ||
        pick.draft_slot < 1 ||
        pick.draft_slot > 8 ||
        !pick.roster_id ||
        !pick.player_id,
    )
  ) {
    return {
      status: "unavailable",
      code: "invalid_pick_snapshot",
      detail:
        "Sleeper picks are not a complete contiguous 8-team draft snapshot.",
    };
  }
  return {
    status: "ready",
    request: {
      source: "sleeper_api",
      observed_at: observedAt,
      declared_complete: true,
      picks: picks.map((pick) => ({
        overall_pick: pick.pick_no,
        team_id: pick.roster_id,
        player: {
          provider: "sleeper",
          external_id: pick.player_id,
          position: asPosition(pick.metadata.position),
          nfl_team: pick.metadata.team,
        },
      })),
    },
    eventIds: picks.map((pick) => sleeperPickEventId(draftId, pick.pick_no)),
  };
}
