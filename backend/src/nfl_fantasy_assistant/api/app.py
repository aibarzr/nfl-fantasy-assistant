"""Loopback-only FastAPI adapter for the neutral v1 protocol."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator

from nfl_fantasy_assistant.application.drafts import (
    ApplicationError,
    DraftEvent,
    DraftService,
    DraftSnapshot,
    ObservedPick,
)
from nfl_fantasy_assistant.application.recommendations import RecommendationRuntime
from nfl_fantasy_assistant.config import credentials_match
from nfl_fantasy_assistant.data.runtime import ActivatedSleeperDataset
from nfl_fantasy_assistant.domain.draft import (
    DraftId,
    DraftSession,
    DraftStatus,
    LeagueConfig,
    LeagueId,
    PlayerReference,
    RosterSlot,
)
from nfl_fantasy_assistant.domain.scoring import ScoringError, validate_scoring_rules
from nfl_fantasy_assistant.persistence import SqliteDraftRepository

API_VERSION = "v1"
MAX_OBSERVATIONS = 256
MAX_TEXT_LENGTH = 256
bearer_scheme = HTTPBearer(auto_error=False)


class ProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorBody(ProtocolModel):
    code: str
    message: str
    request_id: str
    retryable: bool
    details: dict[str, object] = Field(default_factory=dict)


class ErrorEnvelope(ProtocolModel):
    error: ErrorBody


class HealthResponse(ProtocolModel):
    status: Literal["ok"]
    api_version: Literal["v1"]


class ComponentReadiness(ProtocolModel):
    status: Literal["ready", "unavailable", "degraded"]
    detail: str


class DiagnosticsResponse(ProtocolModel):
    api_version: Literal["v1"]
    database: ComponentReadiness
    data: ComponentReadiness
    identity: ComponentReadiness
    adapter: ComponentReadiness
    recommendations: ComponentReadiness


class RosterSlotInput(ProtocolModel):
    name: str = Field(min_length=1, max_length=32)
    eligible_positions: set[Literal["QB", "RB", "WR", "TE", "K", "DEF"]] = Field(min_length=1)
    is_bench: bool = False


class LeagueConfigInput(ProtocolModel):
    config_version: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    team_count: int = Field(ge=2, le=32)
    draft_type: Literal["snake"]
    roster_slots: list[RosterSlotInput] = Field(min_length=1, max_length=32)
    scoring_rules: dict[str, float] = Field(default_factory=dict, max_length=64)
    superflex: bool = False
    te_premium: float = Field(default=0, ge=0, le=10)

    @field_validator("scoring_rules")
    @classmethod
    def supported_scoring_rules(cls, value: dict[str, float]) -> dict[str, float]:
        try:
            validate_scoring_rules(value)
        except ScoringError as error:
            raise ValueError(str(error)) from error
        return value

    def to_domain(self) -> LeagueConfig:
        return LeagueConfig(
            self.config_version,
            self.team_count,
            self.draft_type,
            tuple(
                RosterSlot(slot.name, frozenset(slot.eligible_positions), slot.is_bench)
                for slot in self.roster_slots
            ),
            self.scoring_rules,
            self.superflex,
            self.te_premium,
        )


class PlayerReferenceInput(ProtocolModel):
    provider: str = Field(min_length=1, max_length=64)
    external_id: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    name: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    position: Literal["QB", "RB", "WR", "TE", "K", "DEF"] | None = None
    nfl_team: str | None = Field(default=None, min_length=2, max_length=4)

    def to_domain(self) -> PlayerReference:
        return PlayerReference(
            self.provider, self.external_id, self.name, self.position, self.nfl_team
        )


class ObservedPickInput(ProtocolModel):
    overall_pick: int = Field(ge=1, le=1024)
    team_id: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    player: PlayerReferenceInput

    def to_application(self) -> ObservedPick:
        return ObservedPick(self.overall_pick, self.team_id, self.player.to_domain())


class LeagueCreateRequest(ProtocolModel):
    provider: str = Field(min_length=1, max_length=64)
    provider_league_id: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    config: LeagueConfigInput


class LeagueResponse(ProtocolModel):
    league_id: str
    config_version: str


class DraftCreateRequest(ProtocolModel):
    league_id: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    provider: str = Field(min_length=1, max_length=64)
    provider_draft_id: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    config: LeagueConfigInput
    user_team_id: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    user_slot: int = Field(ge=1, le=1024)
    draft_order: list[str] = Field(min_length=1, max_length=1024)
    dataset_version: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    feature_version: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    model_version: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    initial_picks: list[ObservedPickInput] = Field(
        default_factory=list, max_length=MAX_OBSERVATIONS
    )


class EventRequest(ProtocolModel):
    event_id: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    observed_at: datetime
    surface: Literal["espn", "sleeper", "fantasypros"]
    league_provider: Literal["espn", "sleeper"]
    type: Literal["player_drafted"]
    pick: ObservedPickInput
    protocol_version: Literal["v1"] = "v1"


class SnapshotRequest(ProtocolModel):
    source: Literal["espn", "sleeper_api", "fantasypros"]
    observed_at: datetime
    declared_complete: bool
    picks: list[ObservedPickInput] = Field(max_length=MAX_OBSERVATIONS)


class DraftStateResponse(ProtocolModel):
    draft_id: str
    league_id: str
    status: str
    reconciliation_state: str
    revision: int
    current_pick: int
    dataset_version: str
    feature_version: str
    model_version: str
    accepted_picks: int
    unresolved_observations: int
    issues: list[str]


class EventResponse(ProtocolModel):
    outcome: str
    revision: int
    replayed: bool
    draft: DraftStateResponse


class SnapshotResponse(ProtocolModel):
    outcome: str
    revision: int
    differences: dict[str, object]
    draft: DraftStateResponse


class RecommendationCandidateResponse(ProtocolModel):
    internal_player_id: str
    rank: int
    draft_score: float
    confidence: float
    components: dict[str, float]
    reason_codes: list[str]
    reason_text: str
    warnings: list[str]


class RecommendationResponse(ProtocolModel):
    status: Literal["current"]
    draft_id: str
    revision: int
    generated_at: datetime
    dataset_version: str
    feature_version: str
    model_version: str
    source_updated_at: dict[str, str]
    candidates: list[RecommendationCandidateResponse]


def _state_response(state: object) -> DraftStateResponse:
    # Kept local to the adapter: clients receive a summary, never mutable domain state.
    from nfl_fantasy_assistant.domain.draft import DraftSession

    session = state if isinstance(state, DraftSession) else None
    if session is None:
        raise RuntimeError("draft state response requires a DraftSession")
    return DraftStateResponse(
        draft_id=session.draft_id.value,
        league_id=session.league_id.value,
        status=session.status.value,
        reconciliation_state=session.reconciliation_state.value,
        revision=session.revision,
        current_pick=session.current_pick,
        dataset_version=session.dataset_version,
        feature_version=session.feature_version,
        model_version=session.model_version,
        accepted_picks=len(session.accepted_picks),
        unresolved_observations=len(session.unresolved_observations),
        issues=list(session.issues),
    )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "req_unknown")


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    body = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=_request_id(request),
            retryable=retryable,
            details=details or {},
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def create_app(
    database_path: Path,
    token: str,
    allowed_extension_origin: str,
    sleeper_dataset: ActivatedSleeperDataset | None = None,
) -> FastAPI:
    """Create an app with explicit local dependencies, suitable for safe test injection."""
    if not allowed_extension_origin.startswith("chrome-extension://"):
        raise ValueError("allowed extension origin must be an exact chrome-extension origin")
    repository = SqliteDraftRepository(database_path)
    if sleeper_dataset is not None:
        for player in sleeper_dataset.players:
            repository.save_player(player)
    service = DraftService(repository)
    recommendation_runtime = (
        RecommendationRuntime(sleeper_dataset, repository)
        if sleeper_dataset is not None and sleeper_dataset.recommendations_ready
        else None
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        repository.close()

    app = FastAPI(title="NFL Fantasy Assistant", version=API_VERSION, lifespan=lifespan)
    app.state.repository = repository
    app.state.service = service
    app.state.sleeper_dataset = sleeper_dataset
    app.state.recommendation_runtime = recommendation_runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[allowed_extension_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def correlation_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = f"req_{uuid4().hex}"
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, error: ApplicationError) -> JSONResponse:
        return _error_response(request, error.status_code, error.code, str(error))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        return _error_response(request, 422, "validation_error", "Request validation failed.")

    async def authenticate(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    ) -> None:
        origin = request.headers.get("origin")
        if origin != allowed_extension_origin:
            raise ApplicationError("disallowed_origin", "Request origin is not allowed.", 403)
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise ApplicationError("unauthorized", "Valid bearer authentication is required.", 401)
        try:
            valid = credentials_match(token, credentials.credentials)
        except ValueError:
            valid = False
        if not valid:
            raise ApplicationError("unauthorized", "Valid bearer authentication is required.", 401)

    @app.get("/v1/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", api_version="v1")

    @app.get(
        "/v1/diagnostics",
        response_model=DiagnosticsResponse,
        responses={401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope}},
        dependencies=[Depends(authenticate)],
    )
    async def diagnostics() -> DiagnosticsResponse:
        dataset_ready = sleeper_dataset is not None
        return DiagnosticsResponse(
            api_version="v1",
            database=ComponentReadiness(status="ready", detail="SQLite migrations are current."),
            data=ComponentReadiness(
                status="ready" if dataset_ready else "unavailable",
                detail=(
                    f"Activated immutable Sleeper dataset {sleeper_dataset.dataset_version}."
                    if sleeper_dataset is not None
                    else "No runtime dataset loader is configured."
                ),
            ),
            identity=ComponentReadiness(
                status="ready" if dataset_ready else "degraded",
                detail=(
                    f"Loaded {sleeper_dataset.prepared_count} exact Sleeper prepared-pool mappings."
                    if sleeper_dataset is not None
                    else "Only persisted exact identities are ready."
                ),
            ),
            adapter=ComponentReadiness(
                status="unavailable", detail="No live adapter is active in Phase 3."
            ),
            recommendations=ComponentReadiness(
                status="ready" if recommendation_runtime is not None else "unavailable",
                detail=(
                    "Activated immutable Sleeper recommendation inputs are ready."
                    if recommendation_runtime is not None
                    else "Activated dataset lacks the immutable recommendation-input artifact."
                    if sleeper_dataset is not None
                    else "No runtime dataset loader is configured."
                ),
            ),
        )

    def refresh_recommendations(state: DraftSession) -> None:
        if recommendation_runtime is None:
            return
        if (
            state.provider == "sleeper"
            and state.status is DraftStatus.ACTIVE
            and not state.unresolved_observations
        ):
            recommendation_runtime.generate(state)

    @app.post(
        "/v1/leagues",
        response_model=LeagueResponse,
        responses={409: {"model": ErrorEnvelope}},
        dependencies=[Depends(authenticate)],
    )
    async def create_league(request: LeagueCreateRequest) -> LeagueResponse:
        league_id = service.register_league(
            request.provider, request.provider_league_id, request.config.to_domain()
        )
        return LeagueResponse(
            league_id=league_id.value, config_version=request.config.config_version
        )

    @app.post(
        "/v1/drafts",
        response_model=DraftStateResponse,
        responses={400: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}},
        dependencies=[Depends(authenticate)],
    )
    async def create_draft(request: DraftCreateRequest) -> DraftStateResponse:
        if request.provider == "sleeper":
            if sleeper_dataset is None:
                raise ApplicationError(
                    "sleeper_runtime_unavailable",
                    "Sleeper initialization requires an activated immutable local dataset.",
                    503,
                )
            if (
                request.dataset_version,
                request.feature_version,
                request.model_version,
            ) != (
                sleeper_dataset.dataset_version,
                sleeper_dataset.feature_version,
                sleeper_dataset.model_version,
            ):
                raise ApplicationError(
                    "sleeper_runtime_version_conflict",
                    "Sleeper initialization pins do not match the activated local dataset.",
                    409,
                )
        state = service.initialize_or_resume(
            LeagueId(request.league_id),
            request.provider,
            request.provider_draft_id,
            request.config.to_domain(),
            request.user_team_id,
            request.user_slot,
            tuple(request.draft_order),
            request.dataset_version,
            request.feature_version,
            request.model_version,
            tuple(pick.to_application() for pick in request.initial_picks),
        )
        refresh_recommendations(state)
        return _state_response(state)

    @app.get(
        "/v1/drafts/{draft_id}",
        response_model=DraftStateResponse,
        dependencies=[Depends(authenticate)],
    )
    async def get_draft(draft_id: str) -> DraftStateResponse:
        state = service._require_draft(DraftId(draft_id))
        return _state_response(state)

    @app.post(
        "/v1/drafts/{draft_id}/events",
        response_model=EventResponse,
        dependencies=[Depends(authenticate)],
    )
    async def ingest_event(draft_id: str, request: EventRequest) -> EventResponse:
        if request.observed_at.tzinfo is None:
            raise ApplicationError(
                "invalid_timestamp", "Observation timestamps must include UTC offset."
            )
        result = service.ingest_event(
            DraftId(draft_id),
            DraftEvent(
                request.event_id,
                request.observed_at.astimezone(UTC),
                request.surface,
                request.league_provider,
                request.pick.to_application(),
                request.protocol_version,
            ),
        )
        if not result.replayed:
            refresh_recommendations(result.session)
        return EventResponse(
            outcome=result.outcome,
            revision=result.revision,
            replayed=result.replayed,
            draft=_state_response(result.session),
        )

    @app.post(
        "/v1/drafts/{draft_id}/snapshot",
        response_model=SnapshotResponse,
        dependencies=[Depends(authenticate)],
    )
    async def reconcile_snapshot(draft_id: str, request: SnapshotRequest) -> SnapshotResponse:
        if request.observed_at.tzinfo is None:
            raise ApplicationError(
                "invalid_timestamp", "Snapshot timestamps must include UTC offset."
            )
        result = service.reconcile(
            DraftId(draft_id),
            DraftSnapshot(
                request.source,
                request.observed_at.astimezone(UTC),
                request.declared_complete,
                tuple(pick.to_application() for pick in request.picks),
            ),
        )
        refresh_recommendations(result.session)
        return SnapshotResponse(
            outcome=result.outcome,
            revision=result.revision,
            differences=dict(result.differences),
            draft=_state_response(result.session),
        )

    @app.get(
        "/v1/drafts/{draft_id}/recommendations",
        response_model=RecommendationResponse,
        responses={404: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}},
        dependencies=[Depends(authenticate)],
    )
    async def recommendations(draft_id: str) -> RecommendationResponse:
        state = service._require_draft(DraftId(draft_id))
        if state.provider == "sleeper" and recommendation_runtime is None:
            raise ApplicationError(
                "recommendations_unavailable",
                "The activated Sleeper dataset lacks immutable recommendation inputs.",
                503,
            )
        if state.status.value in {"blocked", "reconciling"}:
            raise ApplicationError(
                "recommendations_not_current",
                "Recommendations are unavailable while draft state is blocked or reconciling.",
                503,
            )
        snapshot = repository.latest_recommendation(DraftId(draft_id))
        if snapshot is None:
            raise ApplicationError(
                "recommendations_unavailable",
                "No current recommendation snapshot is available.",
                503,
            )
        if snapshot.canonical_revision != state.revision:
            raise ApplicationError(
                "recommendations_not_current",
                "Recommendation provenance does not match the current draft revision.",
                503,
            )
        return RecommendationResponse(
            status="current",
            draft_id=draft_id,
            revision=snapshot.canonical_revision,
            generated_at=snapshot.generated_at,
            dataset_version=snapshot.dataset_version,
            feature_version=snapshot.feature_version,
            model_version=snapshot.model_version,
            source_updated_at=dict(snapshot.source_updated_at),
            candidates=[
                RecommendationCandidateResponse(
                    internal_player_id=candidate.internal_player_id,
                    rank=candidate.rank,
                    draft_score=candidate.draft_score,
                    confidence=candidate.confidence,
                    components=dict(candidate.components),
                    reason_codes=list(candidate.reason_codes),
                    reason_text=candidate.reason_text,
                    warnings=list(candidate.warnings),
                )
                for candidate in snapshot.candidates
            ],
        )

    return app
