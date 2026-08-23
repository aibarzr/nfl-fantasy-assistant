/** Exact, provider-specific Sleeper NFL draft-surface recognition. */

export const SLEEPER_DRAFT_ORIGIN = "https://sleeper.com";
export const SLEEPER_DRAFT_HOSTNAME = "sleeper.com";

export type SleeperSurface = {
  supported: true;
  surface: "sleeper_draft";
  leagueProvider: "sleeper";
  draftId: string;
};

export type UnsupportedSleeperSurface = {
  supported: false;
  code: "unsupported_host" | "unsupported_page" | "unsupported_protocol";
  detail: string;
};

export type SleeperSurfaceDetection =
  | SleeperSurface
  | UnsupportedSleeperSurface;

export function detectSleeperDraftSurface(
  location: string | URL,
): SleeperSurfaceDetection {
  let parsed: URL;
  try {
    parsed = typeof location === "string" ? new URL(location) : location;
  } catch {
    return {
      supported: false,
      code: "unsupported_page",
      detail: "The current page URL is not a supported Sleeper draft surface.",
    };
  }
  if (parsed.protocol !== "https:") {
    return {
      supported: false,
      code: "unsupported_protocol",
      detail: "The Sleeper draft surface must use HTTPS.",
    };
  }
  if (parsed.hostname !== SLEEPER_DRAFT_HOSTNAME) {
    return {
      supported: false,
      code: "unsupported_host",
      detail: "This hostname is not the supported Sleeper draft host.",
    };
  }
  const match = /^\/draft\/nfl\/([A-Za-z0-9_-]{6,128})$/.exec(parsed.pathname);
  if (!match) {
    return {
      supported: false,
      code: "unsupported_page",
      detail: "This Sleeper page is not the supported NFL draft surface.",
    };
  }
  return {
    supported: true,
    surface: "sleeper_draft",
    leagueProvider: "sleeper",
    draftId: match[1],
  };
}
