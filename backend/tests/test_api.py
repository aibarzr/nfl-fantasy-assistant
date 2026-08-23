from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from nfl_fantasy_assistant.api import create_app
from nfl_fantasy_assistant.config import generate_token
from nfl_fantasy_assistant.data.runtime import ActivatedSleeperDataset
from nfl_fantasy_assistant.domain.draft import (
    DraftId,
    Player,
    RecommendationCandidate,
    RecommendationSnapshot,
)

ORIGIN = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Origin": ORIGIN}


def league_payload() -> dict[str, object]:
    return {
        "provider": "espn",
        "provider_league_id": "league-1",
        "config": {
            "config_version": "v1",
            "team_count": 8,
            "draft_type": "snake",
            "roster_slots": [
                {"name": "QB", "eligible_positions": ["QB"], "is_bench": False},
                {"name": "BN", "eligible_positions": ["QB", "RB", "WR", "TE"], "is_bench": True},
            ],
            "scoring_rules": {"receptions": 1.0},
        },
    }


def draft_payload(league_id: str) -> dict[str, object]:
    opening = [f"team-{number}" for number in range(1, 9)]
    return {
        "league_id": league_id,
        "provider": "espn",
        "provider_draft_id": "draft-1",
        "config": league_payload()["config"],
        "user_team_id": "team-1",
        "user_slot": 1,
        "draft_order": [*opening, *reversed(opening)],
        "dataset_version": "dataset-v1",
        "feature_version": "feature-v1",
        "model_version": "model-v1",
    }


def test_health_is_safe_and_all_other_resources_require_token_and_origin(tmp_path: Path) -> None:
    token = generate_token()
    app = create_app(tmp_path / "drafts.sqlite3", token, ORIGIN)
    with TestClient(app) as client:
        health = client.get("/v1/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok", "api_version": "v1"}
        assert "X-Request-ID" in health.headers
        assert token not in health.text
        assert client.get("/v1/diagnostics").status_code == 403
        unauthorized = client.get("/v1/diagnostics", headers={"Origin": ORIGIN})
        assert unauthorized.status_code == 401
        assert unauthorized.json()["error"]["code"] == "unauthorized"
        diagnostics = client.get("/v1/diagnostics", headers=headers(token))
        assert diagnostics.status_code == 200
        assert token not in diagnostics.text


def test_api_validates_creates_and_processes_idempotent_event(tmp_path: Path) -> None:
    token = generate_token()
    app = create_app(tmp_path / "drafts.sqlite3", token, ORIGIN)
    app.state.repository.save_player(Player("player-1", {"espn": "1"}, "Safe", "QB"))
    with TestClient(app) as client:
        league = client.post("/v1/leagues", json=league_payload(), headers=headers(token))
        assert league.status_code == 200
        draft = client.post(
            "/v1/drafts", json=draft_payload(league.json()["league_id"]), headers=headers(token)
        )
        assert draft.status_code == 200
        draft_id = draft.json()["draft_id"]
        event = {
            "event_id": "event-1",
            "observed_at": "2026-08-01T12:00:00Z",
            "surface": "espn",
            "league_provider": "espn",
            "type": "player_drafted",
            "pick": {
                "overall_pick": 1,
                "team_id": "team-1",
                "player": {"provider": "espn", "external_id": "1"},
            },
        }
        accepted = client.post(f"/v1/drafts/{draft_id}/events", json=event, headers=headers(token))
        assert accepted.status_code == 200
        assert accepted.json()["outcome"] == "accepted"
        assert (
            client.post(f"/v1/drafts/{draft_id}/events", json=event, headers=headers(token)).json()[
                "replayed"
            ]
            is True
        )
        changed = {
            "event_id": "event-1",
            "observed_at": "2026-08-01T12:00:00Z",
            "surface": "espn",
            "league_provider": "espn",
            "type": "player_drafted",
            "pick": {
                "overall_pick": 1,
                "team_id": "team-1",
                "player": {"provider": "espn", "external_id": "2"},
            },
        }
        conflict = client.post(
            f"/v1/drafts/{draft_id}/events", json=changed, headers=headers(token)
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "event_id_conflict"
        assert (
            client.get(f"/v1/drafts/{draft_id}/recommendations", headers=headers(token)).status_code
            == 503
        )


def test_api_returns_protocol_validation_envelope_without_state_mutation(tmp_path: Path) -> None:
    token = generate_token()
    app = create_app(tmp_path / "drafts.sqlite3", token, ORIGIN)
    with TestClient(app) as client:
        malformed = client.post("/v1/leagues", json={"provider": "espn"}, headers=headers(token))
        assert malformed.status_code == 422
        assert malformed.json()["error"]["code"] == "validation_error"
        assert malformed.json()["error"]["request_id"].startswith("req_")


def test_api_accepts_k_and_def_and_rejects_unknown_scoring_semantics(tmp_path: Path) -> None:
    token = generate_token()
    app = create_app(tmp_path / "drafts.sqlite3", token, ORIGIN)
    config: dict[str, object] = {
        "config_version": "v1",
        "team_count": 8,
        "draft_type": "snake",
        "roster_slots": [
            {"name": "K", "eligible_positions": ["K"], "is_bench": False},
            {"name": "DEF", "eligible_positions": ["DEF"], "is_bench": False},
        ],
        "scoring_rules": {"field_goals_made": 3.0, "defensive_sacks": 1.0},
    }
    payload: dict[str, object] = {
        "provider": "espn",
        "provider_league_id": "league-k-def",
        "config": config,
    }
    with TestClient(app) as client:
        accepted = client.post("/v1/leagues", json=payload, headers=headers(token))
        assert accepted.status_code == 200
        config["scoring_rules"] = {"unknown_rule": 1.0}
        rejected = client.post("/v1/leagues", json=payload, headers=headers(token))
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "validation_error"


def test_api_accepts_sleeper_neutral_k_def_event_and_recovery_contract(tmp_path: Path) -> None:
    token = generate_token()
    app = create_app(
        tmp_path / "drafts.sqlite3",
        token,
        ORIGIN,
        ActivatedSleeperDataset(
            "dataset-fixture",
            "feature-fixture",
            "projection-v3",
            (
                Player("kicker-1", {"sleeper": "sleeper-k"}, "kicker-1", "K"),
                Player("defense-1", {"sleeper": "CHI"}, "defense-1", "DEF", "CHI"),
            ),
            2,
        ),
    )
    config = {
        "config_version": "sleeper-semantic-v3-fixture",
        "team_count": 8,
        "draft_type": "snake",
        "roster_slots": [
            {"name": "K", "eligible_positions": ["K"], "is_bench": False},
            {"name": "DEF", "eligible_positions": ["DEF"], "is_bench": False},
        ],
        "scoring_rules": {
            "field_goals_made_50_plus": 5.0,
            "defensive_points_allowed_0": 10.0,
        },
    }
    opening = [f"team-{number}" for number in range(1, 9)]
    with TestClient(app) as client:
        diagnostics = client.get("/v1/diagnostics", headers=headers(token))
        assert diagnostics.json()["data"]["status"] == "ready"
        assert diagnostics.json()["identity"]["status"] == "ready"
        assert diagnostics.json()["recommendations"]["status"] == "unavailable"
        league = client.post(
            "/v1/leagues",
            json={
                "provider": "sleeper",
                "provider_league_id": "league-fixture",
                "config": config,
            },
            headers=headers(token),
        )
        assert league.status_code == 200
        draft = client.post(
            "/v1/drafts",
            json={
                "league_id": league.json()["league_id"],
                "provider": "sleeper",
                "provider_draft_id": "draft-fixture",
                "config": config,
                "user_team_id": "team-1",
                "user_slot": 1,
                "draft_order": [*opening, *reversed(opening)],
                "dataset_version": "dataset-fixture",
                "feature_version": "feature-fixture",
                "model_version": "projection-v3",
            },
            headers=headers(token),
        )
        assert draft.status_code == 200
        draft_id = draft.json()["draft_id"]
        event = {
            "event_id": "sleeper:draft-fixture:pick:1",
            "observed_at": "2026-08-23T00:00:00Z",
            "surface": "sleeper",
            "league_provider": "sleeper",
            "type": "player_drafted",
            "pick": {
                "overall_pick": 1,
                "team_id": "team-1",
                "player": {"provider": "sleeper", "external_id": "sleeper-k", "position": "K"},
            },
        }
        accepted = client.post(f"/v1/drafts/{draft_id}/events", json=event, headers=headers(token))
        assert accepted.status_code == 200
        snapshot = client.post(
            f"/v1/drafts/{draft_id}/snapshot",
            json={
                "source": "sleeper_api",
                "observed_at": "2026-08-23T00:00:01Z",
                "declared_complete": True,
                "picks": [event["pick"]],
            },
            headers=headers(token),
        )
        assert snapshot.status_code == 200
        assert snapshot.json()["draft"]["accepted_picks"] == 1


def test_api_rejects_unactivated_or_mismatched_sleeper_runtime_pins(tmp_path: Path) -> None:
    token = generate_token()
    app = create_app(tmp_path / "drafts.sqlite3", token, ORIGIN)
    with TestClient(app) as client:
        league = client.post(
            "/v1/leagues",
            json={
                "provider": "sleeper",
                "provider_league_id": "league-fixture",
                "config": league_payload()["config"],
            },
            headers=headers(token),
        )
        rejected = client.post(
            "/v1/drafts",
            json={
                **draft_payload(league.json()["league_id"]),
                "provider": "sleeper",
            },
            headers=headers(token),
        )
        assert rejected.status_code == 503
        assert app.state.repository.find_draft_by_provider("sleeper", "draft-1") is None

    active = create_app(
        tmp_path / "active.sqlite3",
        token,
        ORIGIN,
        ActivatedSleeperDataset(
            "dataset-fixture",
            "feature-fixture",
            "projection-v3",
            (Player("player-1", {"sleeper": "sleeper-1"}, "player-1", "QB"),),
            1,
        ),
    )
    with TestClient(active) as client:
        league = client.post(
            "/v1/leagues",
            json={
                "provider": "sleeper",
                "provider_league_id": "league-fixture",
                "config": league_payload()["config"],
            },
            headers=headers(token),
        )
        rejected = client.post(
            "/v1/drafts",
            json={
                **draft_payload(league.json()["league_id"]),
                "provider": "sleeper",
                "dataset_version": "other-dataset",
            },
            headers=headers(token),
        )
        assert rejected.status_code == 409
        assert active.state.repository.find_draft_by_provider("sleeper", "draft-1") is None


def test_api_rejects_disallowed_origins_and_oversized_mutations_without_draft_state(
    tmp_path: Path,
) -> None:
    token = generate_token()
    app = create_app(tmp_path / "drafts.sqlite3", token, ORIGIN)
    with TestClient(app) as client:
        disallowed = client.post(
            "/v1/leagues",
            json=league_payload(),
            headers={"Authorization": f"Bearer {token}", "Origin": "https://evil.test"},
        )
        assert disallowed.status_code == 403
        assert disallowed.json()["error"]["code"] == "disallowed_origin"
        assert app.state.repository.find_league_by_provider("espn", "league-1") is None

        preflight = client.options(
            "/v1/diagnostics",
            headers={
                "Origin": "https://evil.test",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert preflight.status_code == 400
        assert "access-control-allow-origin" not in preflight.headers

        league = client.post("/v1/leagues", json=league_payload(), headers=headers(token))
        oversized = draft_payload(league.json()["league_id"])
        oversized["initial_picks"] = [
            {
                "overall_pick": index + 1,
                "team_id": "team-1",
                "player": {"provider": "espn", "external_id": str(index)},
            }
            for index in range(257)
        ]
        rejected = client.post("/v1/drafts", json=oversized, headers=headers(token))
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "validation_error"
        assert app.state.repository.find_draft_by_provider("espn", "draft-1") is None


def test_blocked_draft_never_relables_persisted_recommendation_as_current(tmp_path: Path) -> None:
    token = generate_token()
    app = create_app(tmp_path / "drafts.sqlite3", token, ORIGIN)
    app.state.repository.save_player(Player("player-1", {"espn": "1"}, "Safe", "QB"))
    app.state.repository.save_player(Player("player-2", {"espn": "2"}, "Other", "QB"))
    with TestClient(app) as client:
        league = client.post("/v1/leagues", json=league_payload(), headers=headers(token))
        draft = client.post(
            "/v1/drafts", json=draft_payload(league.json()["league_id"]), headers=headers(token)
        )
        draft_id = draft.json()["draft_id"]
        client.post(
            f"/v1/drafts/{draft_id}/events",
            json={
                "event_id": "event-1",
                "observed_at": "2026-08-01T12:00:00Z",
                "surface": "espn",
                "league_provider": "espn",
                "type": "player_drafted",
                "pick": {
                    "overall_pick": 1,
                    "team_id": "team-1",
                    "player": {"provider": "espn", "external_id": "1"},
                },
            },
            headers=headers(token),
        )
        state = app.state.repository.get_draft(DraftId(draft_id))
        assert state is not None
        app.state.repository.save_recommendation(
            RecommendationSnapshot(
                "rec-1",
                state.draft_id,
                state.revision,
                datetime.now(UTC),
                ("player-1", "player-2"),
                (RecommendationCandidate("player-1", 1, 1, 1, {"value": 1}, (), "reason"),),
                state.config.config_version,
                state.dataset_version,
                state.feature_version,
                state.model_version,
                {},
            )
        )
        snapshot = {
            "source": "espn",
            "observed_at": "2026-08-01T12:00:00Z",
            "declared_complete": True,
            "picks": [
                {
                    "overall_pick": 1,
                    "team_id": "team-1",
                    "player": {"provider": "espn", "external_id": "2"},
                }
            ],
        }
        client.post(f"/v1/drafts/{draft_id}/snapshot", json=snapshot, headers=headers(token))
        response = client.get(f"/v1/drafts/{draft_id}/recommendations", headers=headers(token))
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "recommendations_not_current"


def test_api_returns_persisted_recommendation_warnings(tmp_path: Path) -> None:
    token = generate_token()
    app = create_app(tmp_path / "drafts.sqlite3", token, ORIGIN)
    with TestClient(app) as client:
        league = client.post("/v1/leagues", json=league_payload(), headers=headers(token))
        draft = client.post(
            "/v1/drafts", json=draft_payload(league.json()["league_id"]), headers=headers(token)
        )
        state = app.state.repository.get_draft(DraftId(draft.json()["draft_id"]))
        assert state is not None
        app.state.repository.save_recommendation(
            RecommendationSnapshot(
                "rec-warnings",
                state.draft_id,
                state.revision,
                datetime.now(UTC),
                ("player-1",),
                (
                    RecommendationCandidate(
                        "player-1",
                        1,
                        1,
                        1,
                        {"vor": 1},
                        ("vor_advantage",),
                        "Measured VOR advantage.",
                        ("market_stale",),
                    ),
                ),
                state.config.config_version,
                state.dataset_version,
                state.feature_version,
                state.model_version,
                {},
            )
        )
        response = client.get(
            f"/v1/drafts/{state.draft_id.value}/recommendations", headers=headers(token)
        )

    assert response.status_code == 200
    assert response.json()["candidates"][0]["warnings"] == ["market_stale"]
