CREATE TABLE IF NOT EXISTS league_provider_refs (
    provider TEXT NOT NULL,
    provider_league_id TEXT NOT NULL,
    league_id TEXT NOT NULL REFERENCES leagues(league_id),
    PRIMARY KEY(provider, provider_league_id),
    UNIQUE(league_id)
);
