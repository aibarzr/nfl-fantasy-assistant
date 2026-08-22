/** Structured ESPN initialization evidence, kept inside the ESPN adapter boundary. */

import type { components } from "../../api/generated-contract.js";

type DraftCreateRequest = components["schemas"]["DraftCreateRequest"];
type LeagueConfigInput = components["schemas"]["LeagueConfigInput"];

type StructuredInitialSnapshot = {
  team_count: number;
  draft: {
    type_code: string;
    scheduled_pick_order: Array<{ overall_pick: number; team_ref: string }>;
  };
  roster: Record<string, unknown>;
  scoring: Record<string, unknown>;
};

export type InitialSnapshotSource = "structured" | "browser_state" | "dom";

export type VerifiedUserIdentity = {
  userTeamId: string;
  userSlot: number;
};

export type VerifiedLeagueSemantics = {
  codebookVersion: string;
  config: LeagueConfigInput;
};

export type InitialSnapshotContext = {
  source: InitialSnapshotSource;
  providerLeagueId?: string;
  providerDraftId?: string;
  datasetVersion?: string;
  featureVersion?: string;
  modelVersion?: string;
  userIdentity?: VerifiedUserIdentity;
  leagueSemantics?: VerifiedLeagueSemantics;
};

export type SnapshotEvidence = {
  source: InitialSnapshotSource;
  scope: "configuration_and_scheduled_order";
  declaredComplete: false;
  teamCount: number;
  scheduledDraftOrder: string[];
};

export type InitialSnapshotResult =
  | { status: "ready"; evidence: SnapshotEvidence; request: DraftCreateRequest }
  | {
      status: "unavailable";
      code:
        | "unobserved_source"
        | "unsupported_team_count"
        | "unsupported_draft_type"
        | "invalid_draft_order"
        | "user_slot_unavailable"
        | "configuration_codebook_unavailable"
        | "initialization_context_unavailable";
      detail: string;
      evidence?: SnapshotEvidence;
    };

function unavailable(
  code: Extract<InitialSnapshotResult, { status: "unavailable" }>["code"],
  detail: string,
  evidence?: SnapshotEvidence,
): InitialSnapshotResult {
  return { status: "unavailable", code, detail, evidence };
}

function evidenceFrom(
  snapshot: StructuredInitialSnapshot,
  source: InitialSnapshotSource,
): SnapshotEvidence {
  return {
    source,
    scope: "configuration_and_scheduled_order",
    declaredComplete: false,
    teamCount: snapshot.team_count,
    scheduledDraftOrder: snapshot.draft.scheduled_pick_order.map(
      (pick) => pick.team_ref,
    ),
  };
}

function hasValidOrder(snapshot: StructuredInitialSnapshot): boolean {
  const order = snapshot.draft.scheduled_pick_order;
  if (!order.length || order.length % snapshot.team_count !== 0) return false;
  if (
    new Set(order.slice(0, snapshot.team_count).map((pick) => pick.team_ref))
      .size !== snapshot.team_count
  ) {
    return false;
  }
  return order.every(
    (pick, index) =>
      Number.isInteger(pick.overall_pick) &&
      pick.overall_pick === index + 1 &&
      typeof pick.team_ref === "string" &&
      pick.team_ref.length > 0,
  );
}

/**
 * Convert only evidence validated by the caller's user-identity and semantic-codebook sources.
 * Browser-state and DOM sources remain visible unavailable outcomes until canonical captures prove
 * their shapes and completeness.
 */
export function adaptEspnInitialSnapshot(
  snapshot: StructuredInitialSnapshot,
  context: InitialSnapshotContext,
): InitialSnapshotResult {
  if (context.source !== "structured") {
    return unavailable(
      "unobserved_source",
      "This ESPN extraction source has no canonical shape or completeness evidence.",
    );
  }
  const evidence = evidenceFrom(snapshot, context.source);
  if (snapshot.team_count !== 8) {
    return unavailable(
      "unsupported_team_count",
      "Only the supported 8-team ESPN MVP may initialize a draft.",
      evidence,
    );
  }
  if (snapshot.draft.type_code !== "SNAKE") {
    return unavailable(
      "unsupported_draft_type",
      "Only the supported snake-draft configuration may initialize a draft.",
      evidence,
    );
  }
  if (!hasValidOrder(snapshot)) {
    return unavailable(
      "invalid_draft_order",
      "The observed scheduled draft order is incomplete or inconsistent.",
      evidence,
    );
  }
  if (context.userIdentity === undefined) {
    return unavailable(
      "user_slot_unavailable",
      "The active user team and user slot were not observed together.",
      evidence,
    );
  }
  if (context.leagueSemantics === undefined) {
    return unavailable(
      "configuration_codebook_unavailable",
      "No verified ESPN roster and scoring codebook result is available.",
      evidence,
    );
  }
  if (
    !context.providerLeagueId ||
    !context.providerDraftId ||
    !context.datasetVersion ||
    !context.featureVersion ||
    !context.modelVersion
  ) {
    return unavailable(
      "initialization_context_unavailable",
      "Required opaque draft identity or pinned data/model context is unavailable.",
      evidence,
    );
  }
  if (
    context.leagueSemantics.config.team_count !== snapshot.team_count ||
    context.leagueSemantics.config.draft_type !== "snake" ||
    context.userIdentity.userSlot < 1 ||
    context.userIdentity.userSlot > evidence.scheduledDraftOrder.length ||
    evidence.scheduledDraftOrder[context.userIdentity.userSlot - 1] !==
      context.userIdentity.userTeamId
  ) {
    return unavailable(
      "initialization_context_unavailable",
      "The verified semantic configuration or user slot conflicts with observed draft evidence.",
      evidence,
    );
  }
  return {
    status: "ready",
    evidence,
    request: {
      league_id: context.providerLeagueId,
      provider: "espn",
      provider_draft_id: context.providerDraftId,
      config: context.leagueSemantics.config,
      user_team_id: context.userIdentity.userTeamId,
      user_slot: context.userIdentity.userSlot,
      draft_order: evidence.scheduledDraftOrder,
      dataset_version: context.datasetVersion,
      feature_version: context.featureVersion,
      model_version: context.modelVersion,
      initial_picks: [],
    },
  };
}
