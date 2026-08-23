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
});
