import { describe, expect, it, vi } from "vitest";

import { fetchSleeperPlayerLabels } from "../src/adapters/sleeper/api.js";

describe("Sleeper player-label adapter", () => {
  it("reduces the public catalog to only requested non-empty labels", async () => {
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            requested: { full_name: "Requested Player", position: "WR" },
            blank: { full_name: "   " },
            unrelated: { full_name: "Unrelated Player" },
          }),
          { status: 200 },
        ),
    );

    await expect(
      fetchSleeperPlayerLabels(["requested", "blank", "absent"], fetcher),
    ).resolves.toEqual({ requested: "Requested Player" });
    expect(fetcher).toHaveBeenCalledOnce();
  });
});
