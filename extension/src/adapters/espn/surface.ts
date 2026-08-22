/** Exact, provider-specific ESPN draft-surface recognition. */

export const ESPN_DRAFT_ORIGIN = "https://fantasy.espn.com";
export const ESPN_DRAFT_HOSTNAME = "fantasy.espn.com";
export const ESPN_DRAFT_PATHNAME = "/football/draft";

export type EspnSurface = {
  supported: true;
  surface: "espn_draft";
  leagueProvider: "espn";
};

export type UnsupportedSurface = {
  supported: false;
  code: "unsupported_host" | "unsupported_page" | "unsupported_protocol";
  detail: string;
};

export type SurfaceDetection = EspnSurface | UnsupportedSurface;

export function detectEspnDraftSurface(
  location: string | URL,
): SurfaceDetection {
  let parsed: URL;
  try {
    parsed = typeof location === "string" ? new URL(location) : location;
  } catch {
    return {
      supported: false,
      code: "unsupported_page",
      detail: "The current page URL is not a supported ESPN draft surface.",
    };
  }
  if (parsed.protocol !== "https:") {
    return {
      supported: false,
      code: "unsupported_protocol",
      detail: "The ESPN draft surface must use HTTPS.",
    };
  }
  if (parsed.hostname !== ESPN_DRAFT_HOSTNAME) {
    return {
      supported: false,
      code: "unsupported_host",
      detail: "This hostname is not the supported ESPN draft host.",
    };
  }
  if (parsed.pathname !== ESPN_DRAFT_PATHNAME) {
    return {
      supported: false,
      code: "unsupported_page",
      detail: "This ESPN page is not the supported draft surface.",
    };
  }
  return { supported: true, surface: "espn_draft", leagueProvider: "espn" };
}
