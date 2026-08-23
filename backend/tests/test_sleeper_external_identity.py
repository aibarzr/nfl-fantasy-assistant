from __future__ import annotations

from collections.abc import Mapping

import pytest

from nfl_fantasy_assistant.data.errors import DataValidationError
from nfl_fantasy_assistant.data.sleeper_external_identity import (
    SleeperExternalIdentityDecision,
    approve_external_identity_candidates,
    discover_wikidata_candidate,
)
from nfl_fantasy_assistant.data.sleeper_identity import (
    SleeperCatalogRecord,
    SleeperCrosswalkReport,
    merge_external_observed_identities,
)


def _record(*, espn_id: str | None = None) -> SleeperCatalogRecord:
    return SleeperCatalogRecord(
        external_id="sleeper-only",
        position="WR",
        nfl_team="ATL",
        display_name="Example Player",
        espn_id=espn_id,
    )


def test_discovers_one_identifier_bearing_wikidata_candidate() -> None:
    def query(params: Mapping[str, str]) -> Mapping[str, object]:
        if params["action"] == "wbsearchentities":
            return {"search": [{"id": "Q123", "label": "Example Player"}]}
        return {
            "entities": {
                "Q123": {
                    "lastrevid": 42,
                    "labels": {"en": {"value": "Example Player"}},
                    "claims": {
                        "P3686": [{"mainsnak": {"datavalue": {"value": "12345"}}}],
                        "P9338": [{"mainsnak": {"datavalue": {"value": "example-player"}}}],
                    },
                }
            }
        }

    candidate = discover_wikidata_candidate(
        _record(), query=query, retrieved_at="2026-08-23T00:00:00+00:00"
    )

    assert candidate is not None
    assert candidate.wikidata_entity_id == "Q123"
    assert candidate.espn_id == "12345"
    assert candidate.nfl_com_id == "example-player"


def test_approval_requires_catalog_without_an_exact_identifier() -> None:
    candidate = discover_wikidata_candidate(
        _record(),
        query=lambda params: (
            {"search": [{"id": "Q123", "label": "Example Player"}]}
            if params["action"] == "wbsearchentities"
            else {
                "entities": {
                    "Q123": {
                        "labels": {"en": {"value": "Example Player"}},
                        "claims": {"P3686": [{"mainsnak": {"datavalue": {"value": "12345"}}}]},
                    }
                }
            }
        ),
    )
    assert candidate is not None
    decision = SleeperExternalIdentityDecision(
        candidate.external_id,
        candidate.internal_player_id,
        "operator",
        "2026-08-23T00:00:00+00:00",
        "Verified exact identity from the local review candidate.",
    )

    with pytest.raises(DataValidationError, match="without catalog IDs"):
        approve_external_identity_candidates(
            (candidate,),
            (decision,),
            (_record(espn_id="already-exact"),),
            source_manifest_id="catalog",
        )


def test_approved_external_identity_resolves_only_an_unresolved_crosswalk_reference() -> None:
    candidate = discover_wikidata_candidate(
        _record(),
        query=lambda params: (
            {"search": [{"id": "Q123", "label": "Example Player"}]}
            if params["action"] == "wbsearchentities"
            else {
                "entities": {
                    "Q123": {
                        "labels": {"en": {"value": "Example Player"}},
                        "claims": {"P3686": [{"mainsnak": {"datavalue": {"value": "12345"}}}]},
                    }
                }
            }
        ),
    )
    assert candidate is not None
    approved = approve_external_identity_candidates(
        (candidate,),
        (
            SleeperExternalIdentityDecision(
                candidate.external_id,
                candidate.internal_player_id,
                "operator",
                "2026-08-23T00:00:00+00:00",
                "Verified exact identity from the local review candidate.",
            ),
        ),
        (_record(),),
        source_manifest_id="catalog",
    )
    report = SleeperCrosswalkReport(
        source_manifest_id="catalog",
        season=2026,
        mappings=(),
        unresolved_external_ids=("sleeper-only",),
        conflict_external_ids=(),
        coverage_by_position={"WR": (1, 0, 1)},
    )

    merged = merge_external_observed_identities(
        report, (_record(),), approved, review_checksum="review-checksum"
    )

    assert [mapping.external_id for mapping in merged.mappings] == ["sleeper-only"]
    assert not merged.unresolved_external_ids
    assert merged.external_identity_review_checksum == "review-checksum"
