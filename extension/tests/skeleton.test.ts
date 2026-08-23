import { describe, expect, it } from "vitest";

describe("extension manifest", () => {
  it("requests only the exact provider and loopback hosts required by the live loop", async () => {
    const manifest = await import("../manifest.json", {
      with: { type: "json" },
    });

    expect(manifest.default.manifest_version).toBe(3);
    expect(manifest.default.background).toEqual({
      service_worker: "service-worker.js",
    });
    expect(manifest.default.permissions).toEqual(["storage"]);
    expect(manifest.default.host_permissions).toEqual([
      "http://127.0.0.1/*",
      "https://fantasy.espn.com/*",
      "https://sleeper.com/*",
      "https://api.sleeper.app/*",
    ]);
    expect(manifest.default.content_scripts).toEqual([
      {
        matches: ["https://fantasy.espn.com/football/draft*"],
        js: ["content/index.js"],
        run_at: "document_idle",
      },
      {
        matches: ["https://sleeper.com/draft/nfl/*"],
        js: ["content/index.js"],
        run_at: "document_idle",
      },
    ]);
    expect(JSON.stringify(manifest.default)).not.toContain("fantasypros");
  });
});
