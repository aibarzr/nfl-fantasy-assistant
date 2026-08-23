/** Service-worker-only access to the documented, read-only Sleeper draft endpoints. */

import {
  adaptSleeperRecoverySnapshot,
  type SleeperRecoveryResult,
} from "./recovery-snapshot.js";
import {
  adaptSleeperInitializationSnapshot,
  type SleeperInitializationResult,
} from "./initial-snapshot.js";
import type { SleeperInitializationConfiguration } from "../../config/sleeper-initialization.js";
import { detectSleeperDraftSurface } from "./surface.js";

const API_ORIGIN = "https://api.sleeper.app/v1";
const MAX_RESPONSE_BYTES = 512 * 1024;
const MAX_PLAYER_CATALOG_RESPONSE_BYTES = 16 * 1024 * 1024;

type SleeperDraft = {
  draft_id?: string;
  league_id?: string;
  type?: string;
  status?: string;
  sport?: string;
  settings?: { teams?: number; rounds?: number };
  slot_to_roster_id?: Record<string, string | number>;
  draft_order?: Record<string, number> | null;
};

async function getJson(
  fetcher: typeof fetch,
  path: string,
  maxResponseBytes = MAX_RESPONSE_BYTES,
): Promise<unknown> {
  const response = await fetcher(`${API_ORIGIN}${path}`, {
    method: "GET",
    credentials: "omit",
  });
  const contentLength = Number(response.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > maxResponseBytes) {
    throw new Error("Sleeper API response exceeds the adapter safety limit.");
  }
  const payload = await response.text();
  if (!response.ok) {
    throw new Error(
      `Sleeper API request failed with status ${response.status}.`,
    );
  }
  if (payload.length > maxResponseBytes) {
    throw new Error("Sleeper API response exceeds the adapter safety limit.");
  }
  return JSON.parse(payload) as unknown;
}

/** Resolve only requested public catalog labels for local presentation. */
export async function fetchSleeperPlayerLabels(
  externalIds: readonly string[],
  fetcher: typeof fetch = fetch,
): Promise<Record<string, string>> {
  const requested = new Set(externalIds.filter((value) => value.length > 0));
  if (requested.size === 0) return {};
  const catalog = await getJson(
    fetcher,
    "/players/nfl",
    MAX_PLAYER_CATALOG_RESPONSE_BYTES,
  );
  if (
    typeof catalog !== "object" ||
    catalog === null ||
    Array.isArray(catalog)
  ) {
    throw new Error("Sleeper player catalog is not an object.");
  }
  const labels: Record<string, string> = {};
  for (const externalId of requested) {
    const record = (catalog as Record<string, unknown>)[externalId];
    if (
      typeof record === "object" &&
      record !== null &&
      "full_name" in record &&
      typeof record.full_name === "string" &&
      record.full_name.trim().length > 0
    ) {
      labels[externalId] = record.full_name.trim();
    }
  }
  return labels;
}

export async function fetchSleeperRecoverySnapshot(
  pageUrl: string,
  observedAt: string,
  fetcher: typeof fetch = fetch,
): Promise<SleeperRecoveryResult> {
  const surface = detectSleeperDraftSurface(pageUrl);
  if (!surface.supported) {
    return {
      status: "unavailable",
      code: "invalid_draft_identity",
      detail: "Sleeper API retrieval requires the exact active draft surface.",
    };
  }
  const draft = (await getJson(
    fetcher,
    `/draft/${surface.draftId}`,
  )) as SleeperDraft;
  if (
    draft.draft_id !== surface.draftId ||
    draft.type !== "snake" ||
    draft.sport !== "nfl" ||
    draft.settings?.teams !== 8
  ) {
    return {
      status: "unavailable",
      code: "invalid_draft_identity",
      detail:
        "Sleeper draft metadata is not the supported 8-team NFL snake draft.",
    };
  }
  if (
    !draft.slot_to_roster_id ||
    Object.keys(draft.slot_to_roster_id).length !== 8 ||
    !Array.from({ length: 8 }, (_, index) => String(index + 1)).every(
      (slot) =>
        (typeof draft.slot_to_roster_id?.[slot] === "string" ||
          typeof draft.slot_to_roster_id?.[slot] === "number") &&
        `${draft.slot_to_roster_id[slot]}`.length > 0,
    ) ||
    new Set(Object.values(draft.slot_to_roster_id)).size !== 8
  ) {
    return {
      status: "unavailable",
      code: "invalid_draft_identity",
      detail: "Sleeper draft metadata has no complete slot-to-roster mapping.",
    };
  }
  const picks = await getJson(fetcher, `/draft/${surface.draftId}/picks`);
  if (!Array.isArray(picks)) {
    return {
      status: "unavailable",
      code: "invalid_pick_snapshot",
      detail: "Sleeper picks response is not an array.",
    };
  }
  return adaptSleeperRecoverySnapshot(
    surface.draftId,
    picks,
    observedAt,
    Object.fromEntries(
      Object.entries(draft.slot_to_roster_id).map(([slot, rosterId]) => [
        slot,
        `${rosterId}`,
      ]),
    ),
  );
}

/**
 * Reads only the documented facts required to construct a neutral initialization handoff.
 * The caller owns local readiness and the paired backend mutation; raw responses stay in memory.
 */
export async function fetchSleeperInitializationSnapshot(
  pageUrl: string,
  observedAt: string,
  context: SleeperInitializationConfiguration,
  fetcher: typeof fetch = fetch,
): Promise<SleeperInitializationResult> {
  const surface = detectSleeperDraftSurface(pageUrl);
  if (!surface.supported) {
    return {
      status: "unavailable",
      code: "invalid_draft_identity",
      detail: "Sleeper initialization requires the exact active draft surface.",
    };
  }
  const draft = (await getJson(
    fetcher,
    `/draft/${surface.draftId}`,
  )) as SleeperDraft;
  if (typeof draft.league_id !== "string" || draft.league_id.length === 0) {
    return {
      status: "unavailable",
      code: "invalid_league_identity",
      detail:
        "The active Sleeper draft has no league-backed initialization identity.",
    };
  }
  const [league, rosters, users, picks] = await Promise.all([
    getJson(fetcher, `/league/${draft.league_id}`),
    getJson(fetcher, `/league/${draft.league_id}/rosters`),
    getJson(fetcher, `/league/${draft.league_id}/users`),
    getJson(fetcher, `/draft/${surface.draftId}/picks`),
  ]);
  return adaptSleeperInitializationSnapshot({
    draftId: surface.draftId,
    draft,
    league: league as Record<string, unknown>,
    rosters,
    users,
    picks,
    observedAt,
    context,
  });
}
