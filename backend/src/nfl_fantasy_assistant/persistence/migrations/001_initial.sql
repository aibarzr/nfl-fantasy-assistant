CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leagues (
    league_id TEXT PRIMARY KEY,
    config_version TEXT NOT NULL,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    draft_id TEXT PRIMARY KEY,
    league_id TEXT NOT NULL REFERENCES leagues(league_id),
    provider TEXT NOT NULL,
    provider_draft_id TEXT NOT NULL,
    user_team_id TEXT NOT NULL,
    user_slot INTEGER NOT NULL,
    draft_order_json TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    model_version TEXT NOT NULL,
    status TEXT NOT NULL,
    reconciliation_state TEXT NOT NULL,
    revision INTEGER NOT NULL,
    issues_json TEXT NOT NULL,
    UNIQUE(provider, provider_draft_id)
);

CREATE TABLE IF NOT EXISTS players (
    internal_player_id TEXT PRIMARY KEY,
    player_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS player_external_ids (
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    internal_player_id TEXT NOT NULL REFERENCES players(internal_player_id),
    PRIMARY KEY(provider, external_id)
);

CREATE TABLE IF NOT EXISTS picks (
    draft_id TEXT NOT NULL REFERENCES drafts(draft_id),
    overall_pick INTEGER NOT NULL,
    team_id TEXT NOT NULL,
    internal_player_id TEXT NOT NULL REFERENCES players(internal_player_id),
    source TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    event_id TEXT,
    PRIMARY KEY(draft_id, overall_pick),
    UNIQUE(draft_id, internal_player_id)
);

CREATE TABLE IF NOT EXISTS unresolved_observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id TEXT NOT NULL REFERENCES drafts(draft_id),
    observation_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_outcomes (
    draft_id TEXT NOT NULL REFERENCES drafts(draft_id),
    event_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    outcome TEXT NOT NULL,
    resulting_revision INTEGER NOT NULL,
    PRIMARY KEY(draft_id, event_id)
);

CREATE TABLE IF NOT EXISTS reconciliation_records (
    reconciliation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id TEXT NOT NULL REFERENCES drafts(draft_id),
    source TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    declared_complete INTEGER NOT NULL,
    differences_json TEXT NOT NULL,
    outcome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendation_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL REFERENCES drafts(draft_id),
    canonical_revision INTEGER NOT NULL,
    is_current INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS recommendation_snapshots_latest
ON recommendation_snapshots(draft_id, canonical_revision DESC, created_at DESC);
