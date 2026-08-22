import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const fixtureDirectory = resolve(root, "docs/sleeper-data");

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};

const readFixture = async (name) =>
  JSON.parse(await readFile(resolve(fixtureDirectory, name), "utf8"));

const recovery = await readFixture("sleeper-8-team-recovery-snapshot.json");
const references = await readFixture("sleeper-asset-reference-sample.json");
const fixtures = new Map([
  ["sleeper-8-team-recovery-snapshot.json", recovery],
  ["sleeper-asset-reference-sample.json", references],
]);
const forbidden = [
  /accessToken/i,
  /refreshToken/i,
  /authorization/i,
  /cookie/i,
  /https?:\/\//i,
  /fullName/i,
  /firstName/i,
  /lastName/i,
  /[0-9]{12,}/,
];

for (const [name, fixture] of fixtures) {
  const serialized = JSON.stringify(fixture);
  assert(fixture.fixture_metadata !== undefined, `${name} lacks fixture metadata.`);
  assert(
    fixture.fixture_metadata.source_class === "synthetic_validation_input",
    `${name} must be explicitly synthetic.`,
  );
  assert(!forbidden.some((pattern) => pattern.test(serialized)), `${name} contains forbidden data.`);
}

assert(recovery.draft.type === "snake", "Recovery fixture must be snake.");
assert(recovery.draft.status === "drafting", "Recovery fixture must be in progress.");
assert(recovery.draft.sport === "nfl", "Recovery fixture must be NFL.");
assert(recovery.draft.settings.teams === 8, "Recovery fixture must be 8-team.");
assert(recovery.draft.settings.rounds === 13, "Recovery fixture must have 13 rounds.");
assert(Object.keys(recovery.draft.slot_to_roster_id).length === 8, "Recovery fixture lacks slots.");
assert(recovery.draft.draft_order["user-fixture"] === 7, "Recovery fixture lacks user slot evidence.");

const pickNumbers = recovery.picks.map((pick) => pick.pick_no);
assert(
  pickNumbers.every((pickNumber, index) => pickNumber === index + 1),
  "Recovery picks must be ordered and contiguous from one.",
);
assert(
  recovery.picks.every(
    (pick) =>
      pick.draft_id === recovery.draft.draft_id &&
      typeof pick.player_id === "string" &&
      pick.player_id.length > 0 &&
      Number.isInteger(pick.draft_slot) &&
      Number.isInteger(pick.round) &&
      pick.roster_id.startsWith("roster-fixture-") &&
      pick.metadata?.player_id === pick.player_id &&
      pick.metadata?.sport === "nfl",
  ),
  "Recovery pick shape is invalid.",
);

assert(
  references.player_references.some(
    (reference) => reference.position === "K" && reference.external_id.startsWith("player-fixture-"),
  ),
  "Reference fixture lacks an individual-player kicker.",
);
assert(
  references.player_references.some(
    (reference) =>
      reference.position === "DEF" &&
      reference.external_id.startsWith("defense-fixture-") &&
      reference.nfl_team.startsWith("team-fixture-"),
  ),
  "Reference fixture lacks an exact team-defense reference.",
);

console.log(`Validated ${fixtures.size} sanitized Sleeper discovery fixtures.`);
