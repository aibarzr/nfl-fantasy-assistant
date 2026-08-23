import fixture from "../../docs/sleeper-data/sleeper-8-team-recovery-snapshot.json" with {
  type: "json",
};
import { describe, expect, it } from "vitest";

import {
  adaptSleeperRecoverySnapshot,
  sleeperPickEventId,
} from "../src/adapters/sleeper/recovery-snapshot.js";
import { fetchSleeperRecoverySnapshot } from "../src/adapters/sleeper/api.js";
import { detectSleeperDraftSurface } from "../src/adapters/sleeper/surface.js";

describe("Sleeper recovery adapter", () => {
  it("recognizes only the confirmed NFL draft path", () => {
    expect(
      detectSleeperDraftSurface("https://sleeper.com/draft/nfl/draft-fixture"),
    ).toMatchObject({ supported: true, surface: "sleeper_draft" });
    for (const url of [
      "http://sleeper.com/draft/nfl/draft-fixture",
      "https://sleeper.com/draft/nba/draft-fixture",
      "https://sleeper.com/draft/nfl/short",
      "https://sleeper.com/draft/nfl/draft-fixture/extra",
      "https://sleeper.com.evil.test/draft/nfl/draft-fixture",
    ]) {
      expect(detectSleeperDraftSurface(url).supported).toBe(false);
    }
  });

  it("creates only a complete neutral recovery snapshot and deterministic event IDs", () => {
    const result = adaptSleeperRecoverySnapshot(
      fixture.draft.draft_id,
      fixture.picks,
      "2026-08-23T00:00:00Z",
    );
    expect(result).toMatchObject({ status: "ready" });
    if (result.status === "ready") {
      expect(result.request).toMatchObject({
        source: "sleeper_api",
        declared_complete: true,
      });
      expect(result.request.picks[0]).toMatchObject({
        player: { provider: "sleeper", position: "RB" },
      });
    }
    expect(sleeperPickEventId("draft-fixture", 1)).toBe(
      "sleeper:draft-fixture:pick:1",
    );
  });

  it("retains supported K/DEF references and validates snake reversal after round one", () => {
    const picks = Array.from({ length: 9 }, (_, index) => {
      const pickNumber = index + 1;
      const draftSlot = pickNumber <= 8 ? pickNumber : 8;
      const playerId = `player-fixture-${String(pickNumber).padStart(2, "0")}`;
      const position = pickNumber === 1 ? "K" : pickNumber === 9 ? "DEF" : "RB";
      return {
        draft_id: fixture.draft.draft_id,
        pick_no: pickNumber,
        draft_slot: draftSlot,
        roster_id: `roster-fixture-${draftSlot}`,
        player_id: playerId,
        metadata: { player_id: playerId, position, sport: "nfl" },
      };
    });
    const result = adaptSleeperRecoverySnapshot(
      fixture.draft.draft_id,
      picks,
      "2026-08-23T00:00:00Z",
      fixture.draft.slot_to_roster_id,
    );
    expect(result).toMatchObject({ status: "ready" });
    if (result.status === "ready") {
      expect(result.request.picks[0].player.position).toBe("K");
      expect(result.request.picks[8].player.position).toBe("DEF");
      expect(result.eventIds[8]).toBe("sleeper:draft-fixture:pick:9");
    }
  });

  it("normalizes an unordered, numeric-roster current pick prefix before validation", () => {
    const picks = Array.from({ length: 11 }, (_, index) => {
      const pickNumber = index + 1;
      const draftSlot =
        pickNumber <= 8 ? pickNumber : 8 - ((pickNumber - 1) % 8);
      const playerId = `player-fixture-${String(pickNumber).padStart(2, "0")}`;
      return {
        draft_id: fixture.draft.draft_id,
        pick_no: pickNumber,
        draft_slot: draftSlot,
        roster_id: draftSlot,
        player_id: playerId,
        metadata: { player_id: playerId, position: "RB", sport: "nfl" },
      };
    }).reverse();
    const slotToRosterId = Object.fromEntries(
      Array.from({ length: 8 }, (_, index) => [
        String(index + 1),
        String(index + 1),
      ]),
    );

    const result = adaptSleeperRecoverySnapshot(
      fixture.draft.draft_id,
      picks,
      "2026-08-23T00:00:00Z",
      slotToRosterId,
    );

    expect(result).toMatchObject({ status: "ready" });
    if (result.status === "ready") {
      expect(result.request.picks.map((pick) => pick.overall_pick)).toEqual(
        Array.from({ length: 11 }, (_, index) => index + 1),
      );
    }
  });

  it("rejects cross-scoped or non-contiguous snapshots before backend submission", () => {
    expect(
      adaptSleeperRecoverySnapshot(
        "other-draft",
        fixture.picks,
        "2026-08-23T00:00:00Z",
      ),
    ).toMatchObject({ status: "unavailable", code: "invalid_draft_identity" });
    expect(
      adaptSleeperRecoverySnapshot(
        fixture.draft.draft_id,
        [{ ...fixture.picks[0], pick_no: 2 }],
        "2026-08-23T00:00:00Z",
      ),
    ).toMatchObject({ status: "unavailable", code: "invalid_pick_snapshot" });
    expect(
      adaptSleeperRecoverySnapshot(
        fixture.draft.draft_id,
        [{ ...fixture.picks[0], draft_slot: 8 }],
        "2026-08-23T00:00:00Z",
      ),
    ).toMatchObject({ status: "unavailable", code: "invalid_pick_snapshot" });
    expect(
      adaptSleeperRecoverySnapshot(
        fixture.draft.draft_id,
        [{ ...fixture.picks[0], metadata: { position: "UNKNOWN" } }],
        "2026-08-23T00:00:00Z",
      ),
    ).toMatchObject({ status: "unavailable", code: "invalid_pick_snapshot" });
    expect(
      adaptSleeperRecoverySnapshot(
        fixture.draft.draft_id,
        fixture.picks,
        "2026-08-23T00:00:00Z",
        { ...fixture.draft.slot_to_roster_id, "1": "wrong-roster" },
      ),
    ).toMatchObject({ status: "unavailable", code: "invalid_draft_identity" });
  });

  it("fetches only documented draft and picks endpoints after exact-surface activation", async () => {
    const requested: string[] = [];
    const fetcher = async (url: string | URL) => {
      requested.push(String(url));
      const payload = String(url).endsWith("/picks")
        ? fixture.picks
        : fixture.draft;
      return new Response(JSON.stringify(payload), { status: 200 });
    };
    await expect(
      fetchSleeperRecoverySnapshot(
        "https://sleeper.com/draft/nfl/draft-fixture",
        "2026-08-23T00:00:00Z",
        fetcher as typeof fetch,
      ),
    ).resolves.toMatchObject({ status: "ready" });
    expect(requested).toEqual([
      "https://api.sleeper.app/v1/draft/draft-fixture",
      "https://api.sleeper.app/v1/draft/draft-fixture/picks",
    ]);
  });

  it("does not read picks when draft identity lacks a complete slot mapping", async () => {
    const requested: string[] = [];
    const draftWithoutSlots = {
      ...fixture.draft,
      slot_to_roster_id: undefined,
    };
    const fetcher = async (url: string | URL) => {
      requested.push(String(url));
      return new Response(JSON.stringify(draftWithoutSlots), { status: 200 });
    };
    await expect(
      fetchSleeperRecoverySnapshot(
        "https://sleeper.com/draft/nfl/draft-fixture",
        "2026-08-23T00:00:00Z",
        fetcher as typeof fetch,
      ),
    ).resolves.toMatchObject({
      status: "unavailable",
      code: "invalid_draft_identity",
    });
    expect(requested).toHaveLength(1);
  });

  it("rejects a non-unique draft slot-to-roster mapping before reading picks", async () => {
    const requested: string[] = [];
    const draftWithDuplicateRoster = {
      ...fixture.draft,
      slot_to_roster_id: {
        ...fixture.draft.slot_to_roster_id,
        "8": fixture.draft.slot_to_roster_id["7"],
      },
    };
    const fetcher = async (url: string | URL) => {
      requested.push(String(url));
      return new Response(JSON.stringify(draftWithDuplicateRoster), {
        status: 200,
      });
    };
    await expect(
      fetchSleeperRecoverySnapshot(
        "https://sleeper.com/draft/nfl/draft-fixture",
        "2026-08-23T00:00:00Z",
        fetcher as typeof fetch,
      ),
    ).resolves.toMatchObject({
      status: "unavailable",
      code: "invalid_draft_identity",
    });
    expect(requested).toHaveLength(1);
  });
});
