CREATE TABLE IF NOT EXISTS player_status_overlays (
    overlay_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS player_status_overlays_latest
ON player_status_overlays(provider, dataset_version, observed_at DESC, created_at DESC);
