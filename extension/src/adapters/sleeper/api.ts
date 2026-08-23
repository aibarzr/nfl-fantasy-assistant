/** Service-worker-only access to the documented, read-only Sleeper draft endpoints. */

import {
  adaptSleeperRecoverySnapshot,
  type SleeperRecoveryResult,
} from "./recovery-snapshot.js";
import { detectSleeperDraftSurface } from "./surface.js";

const API_ORIGIN = "https://api.sleeper.app/v1";
const MAX_RESPONSE_BYTES = 512 * 1024;

type SleeperDraft = {
  draft_id?: string;
  type?: string;
  sport?: string;
  settings?: { teams?: number };
  slot_to_roster_id?: Record<string, string>;
};

async function getJson(fetcher: typeof fetch, path: string): Promise<unknown> {
  const response = await fetcher(`${API_ORIGIN}${path}`, {
    method: "GET",
    credentials: "omit",
  });
  const contentLength = Number(response.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > MAX_RESPONSE_BYTES) {
    throw new Error("Sleeper API response exceeds the adapter safety limit.");
  }
  const payload = await response.text();
  if (!response.ok) {
    throw new Error(
      `Sleeper API request failed with status ${response.status}.`,
    );
  }
  if (payload.length > MAX_RESPONSE_BYTES) {
    throw new Error("Sleeper API response exceeds the adapter safety limit.");
  }
  return JSON.parse(payload) as unknown;
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
        typeof draft.slot_to_roster_id?.[slot] === "string" &&
        draft.slot_to_roster_id[slot].length > 0,
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
    draft.slot_to_roster_id,
  );
}
