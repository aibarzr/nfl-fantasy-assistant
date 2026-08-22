import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const rawDirectory = resolve(root, "data/raw/espn");
const outputDirectory = resolve(root, "docs/espn-data");

const readJson = async (name) =>
  JSON.parse(await readFile(resolve(rawDirectory, name), "utf8"));

const writeFixture = async (name, value) => {
  const serialized = `${JSON.stringify(value, null, 2)}\n`;
  const forbidden = [
    /accessToken/i,
    /refreshToken/i,
    /authorization/i,
    /cookie/i,
    /leagueId/i,
    /memberId/i,
    /https:\/\//i,
  ];
  if (forbidden.some((pattern) => pattern.test(serialized))) {
    throw new Error(`Refusing to write unsafe fixture ${name}.`);
  }
  await writeFile(resolve(outputDirectory, name), serialized, "utf8");
};

const rawSnapshot = await readJson("draft-petition-01.json");
const rawHar = await readJson("wss-har.json");
await mkdir(outputDirectory, { recursive: true });

const teamIds = [...new Set(rawSnapshot.draftDetail.picks.map((pick) => pick.teamId))];
const teamAliases = new Map(teamIds.map((teamId, index) => [teamId, `team-${index + 1}`]));
const teamAlias = (teamId) => {
  const alias = teamAliases.get(teamId);
  if (alias === undefined) {
    throw new Error("A captured team reference was absent from the scheduled draft order.");
  }
  return alias;
};

const scoringItems = rawSnapshot.settings.scoringSettings.scoringItems.map((item) => ({
  stat_id: item.statId,
  points: item.points,
  is_reverse_item: item.isReverseItem,
  points_overrides: item.pointsOverrides,
}));

const selectedObservations = rawHar.log.entries.flatMap((entry) =>
  (entry._webSocketMessages ?? []).flatMap((message) => {
    const match = /^SELECTED\s+(\d+)\s+(-?\d+)\s+(\d+)/.exec(message.data);
    if (match === null) {
      return [];
    }
    const [, rawTeamId, playerId, trailingNumericCode] = match;
    return [
      {
        transport_direction: message.type,
        team_ref: teamAlias(Number(rawTeamId)),
        player: { provider: "espn", external_id: playerId },
        source_trailing_numeric_code: Number(trailingNumericCode),
      },
    ];
  }),
);

const selectedEvents = selectedObservations
  .map((event, index) => ({
    observation_id: `wss-selected-${String(index + 1).padStart(3, "0")}`,
    ...event,
  }));

const byPosition = new Map();
for (const entry of rawSnapshot.players) {
  const player = entry.player;
  if (!byPosition.has(player.defaultPositionId)) {
    byPosition.set(player.defaultPositionId, {
      provider: "espn",
      external_id: String(player.id),
      position_code: player.defaultPositionId,
      pro_team_code: player.proTeamId,
      eligible_slot_codes: player.eligibleSlots,
    });
  }
}
const playerReferenceSample = [...byPosition.values()].sort(
  (left, right) => left.position_code - right.position_code,
);

const fixtureMetadata = {
  source_class: "sanitized_derived_capture",
  surface: "espn_draft",
  league_provider: "espn",
  captured_on: "2026-07-30",
  sanitization: {
    removed: [
      "all request URLs and headers",
      "session credentials",
      "direct account-scope identifiers",
      "display names, logos, and unrelated payload fields",
    ],
    team_references: "Stable fixture-local aliases in scheduled-draft-order order.",
  },
};

await writeFixture("espn-8-team-initial-snapshot.json", {
  fixture_metadata: {
    ...fixtureMetadata,
    completeness: "configuration and scheduled snake order; this response does not establish accepted picks",
    expected_parser_outcome: "supported initial snapshot for an 8-team snake draft",
  },
  snapshot: {
    team_count: rawSnapshot.settings.size,
    draft: {
      type_code: rawSnapshot.settings.draftSettings.type,
      order_type_code: rawSnapshot.settings.draftSettings.orderType,
      scheduled_pick_order: rawSnapshot.draftDetail.picks.map((pick) => ({
        overall_pick: pick.id,
        team_ref: teamAlias(pick.teamId),
      })),
    },
    roster: {
      lineup_slot_counts: rawSnapshot.settings.rosterSettings.lineupSlotCounts,
      position_limits: rawSnapshot.settings.rosterSettings.positionLimits,
    },
    scoring: {
      type_code: rawSnapshot.settings.scoringSettings.scoringType,
      items: scoringItems,
    },
  },
});

await writeFixture("espn-8-team-selected-picks.json", {
  fixture_metadata: {
    ...fixtureMetadata,
    completeness: "observed SELECTED WebSocket messages only; not an authoritative recovery snapshot",
    expected_parser_outcome:
      "normalized pick observations with unique fixture-local observation IDs; source_trailing_numeric_code semantics and idempotency must be investigated before an event rule is accepted",
  },
  events: selectedEvents,
});

await writeFixture("espn-player-reference-sample.json", {
  fixture_metadata: {
    ...fixtureMetadata,
    completeness: "one observed ESPN player reference per position code; no name-based identity data retained",
    expected_parser_outcome:
      "provider and external_id form the primary reference; position/team codes are corroborating attributes only",
  },
  player_references: playerReferenceSample,
});

console.log(
  `Wrote three sanitized fixtures from ${selectedObservations.length} observed selected-pick messages and ${playerReferenceSample.length} position samples.`,
);
