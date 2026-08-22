import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const fixtureDirectory = resolve(root, "docs/espn-data");

const readFixture = async (name) =>
  JSON.parse(await readFile(resolve(fixtureDirectory, name), "utf8"));

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};

const fixtureNames = [
  "espn-8-team-initial-snapshot.json",
  "espn-8-team-selected-picks.json",
  "espn-player-reference-sample.json",
  "synthetic-unsupported-team-count-10.json",
];
const forbidden = [
  /accessToken/i,
  /refreshToken/i,
  /authorization/i,
  /cookie/i,
  /leagueId/i,
  /memberId/i,
  /fullName/i,
  /firstName/i,
  /lastName/i,
  /https?:\/\//i,
];

const fixtures = new Map();
for (const name of fixtureNames) {
  const fixture = await readFixture(name);
  const serialized = JSON.stringify(fixture);
  assert(!forbidden.some((pattern) => pattern.test(serialized)), `${name} contains forbidden data.`);
  assert(fixture.fixture_metadata !== undefined, `${name} lacks fixture metadata.`);
  fixtures.set(name, fixture);
}

const initial = fixtures.get("espn-8-team-initial-snapshot.json");
assert(initial.snapshot.team_count === 8, "Initial fixture must represent the supported 8-team MVP.");
assert(initial.snapshot.draft.scheduled_pick_order.length > 0, "Initial fixture lacks draft order.");
assert(
  initial.snapshot.draft.scheduled_pick_order.every((pick) => /^team-[1-8]$/.test(pick.team_ref)),
  "Initial fixture contains a non-sanitized team reference.",
);

const events = fixtures.get("espn-8-team-selected-picks.json").events;
const observationIds = events.map((event) => event.observation_id);
assert(
  observationIds.length === new Set(observationIds).size,
  "Selected-pick fixture contains duplicate observation IDs.",
);
assert(
  events.every(
    (event) =>
      /^team-[1-8]$/.test(event.team_ref) && /^-?\d+$/.test(event.player.external_id) &&
      Number.isInteger(event.source_trailing_numeric_code),
  ),
  "Selected-pick fixture contains an invalid normalized observation.",
);
assert(
  events.length === initial.snapshot.draft.scheduled_pick_order.length,
  "The complete selected-pick fixture must cover every scheduled pick.",
);
assert(
  events.every(
    (event, index) =>
      event.team_ref === initial.snapshot.draft.scheduled_pick_order[index].team_ref,
  ),
  "Selected-pick observations do not follow the captured scheduled draft order.",
);
assert(
  new Set(events.map((event) => event.player.external_id)).size === events.length,
  "The complete selected-pick fixture contains a duplicate player reference.",
);

const playerReferences = fixtures.get("espn-player-reference-sample.json").player_references;
assert(playerReferences.length > 0, "Player-reference fixture is empty.");
assert(
  playerReferences.every(
    (reference) => reference.provider === "espn" && /^-?\d+$/.test(reference.external_id),
  ),
  "Player-reference fixture lacks ESPN external identifiers.",
);

const unsupported = fixtures.get("synthetic-unsupported-team-count-10.json");
assert(
  unsupported.fixture_metadata.source_class === "synthetic_validation_input" &&
    unsupported.normalized_observation.team_count === 10 &&
    unsupported.fixture_metadata.expected_parser_outcome.reason_code === "unsupported_team_count",
  "Unsupported-team-count fixture does not describe the intended synthetic rejection.",
);

console.log(`Validated ${fixtureNames.length} sanitized ESPN spike fixtures.`);
