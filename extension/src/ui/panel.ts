/** Isolated, read-only presentation of backend-owned recommendation state. */

import type { components } from "../api/generated-contract.js";

type Candidate = components["schemas"]["RecommendationCandidateResponse"];
export type RecommendationResponse =
  components["schemas"]["RecommendationResponse"];

export type RecommendationPanelState =
  | { kind: "loading"; detail: string }
  | { kind: "current"; recommendation: RecommendationResponse }
  | { kind: "empty"; detail: string }
  | { kind: "stale" | "blocked"; detail: string }
  | {
      kind: "disconnected" | "unauthorized" | "incompatible" | "error";
      detail: string;
      retryable: boolean;
    };

const componentLabels: Record<string, string> = {
  market: "Market",
  roster: "Roster fit",
  risk_upside: "Risk / upside",
  scarcity: "Scarcity",
  urgency: "Next-turn urgency",
  vor: "VOR",
};

function text(value: string): string {
  return value.replace(/[&<>'"]/g, (character) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    };
    return entities[character] ?? character;
  });
}

function score(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function candidateMarkup(candidate: Candidate): string {
  const components = Object.entries(candidate.components)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(
      ([name, value]) => `
        <li><span>${text(componentLabels[name] ?? name)}</span><strong>${typeof value === "number" ? score(value) : "—"}</strong></li>`,
    )
    .join("");
  const warnings = candidate.warnings
    .map((warning) => `<li>${text(warning)}</li>`)
    .join("");
  return `
    <article class="candidate">
      <div class="candidate__rank" aria-label="Rank ${candidate.rank}">${candidate.rank}</div>
      <div class="candidate__body">
        <header><code>${text(candidate.internal_player_id)}</code><strong>${score(candidate.draft_score)}</strong></header>
        <p class="reason">${text(candidate.reason_text)}</p>
        <p class="codes">${candidate.reason_codes.map(text).join(" · ") || "Measured components"}</p>
        <dl class="metrics"><div><dt>Confidence</dt><dd>${score(candidate.confidence)}</dd></div></dl>
        <ul class="components">${components}</ul>
        ${warnings ? `<ul class="warnings" aria-label="Warnings">${warnings}</ul>` : ""}
      </div>
    </article>`;
}

function stateMarkup(state: RecommendationPanelState): string {
  if (state.kind === "current") {
    const { recommendation } = state;
    if (recommendation.candidates.length === 0) {
      return `<section class="state state--empty"><p>No eligible recommendations are currently available.</p></section>`;
    }
    return `
      <section class="recommendations" aria-label="Current recommendations">
        ${recommendation.candidates.map(candidateMarkup).join("")}
        <footer class="provenance">
          <span>Revision ${recommendation.revision}</span>
          <span>Model ${text(recommendation.model_version)}</span>
          <span>Features ${text(recommendation.feature_version)}</span>
          <span>Dataset ${text(recommendation.dataset_version)}</span>
          <time datetime="${text(recommendation.generated_at)}">${text(recommendation.generated_at)}</time>
        </footer>
      </section>`;
  }
  const title = {
    blocked: "Recommendations paused",
    disconnected: "Backend disconnected",
    empty: "No recommendation yet",
    error: "Recommendation error",
    incompatible: "Backend update required",
    loading: "Updating draft board",
    stale: "Recommendations stale",
    unauthorized: "Pairing required",
  }[state.kind];
  const retry =
    "retryable" in state && state.retryable ? " It is safe to retry." : "";
  return `<section class="state state--${state.kind}" role="status"><h2>${title}</h2><p>${text(state.detail)}${retry}</p></section>`;
}

const styles = `
  :host { all: initial; color: #f4ead7; font-family: ui-serif, "Iowan Old Style", "Palatino Linotype", serif; }
  *, *::before, *::after { box-sizing: border-box; }
  .shell { position: fixed; right: 18px; bottom: 18px; width: min(390px, calc(100vw - 36px)); max-height: min(78vh, 760px); overflow: auto; z-index: 2147483647; background: #111a21; border: 1px solid #cf9d48; box-shadow: 8px 9px 0 #05080b, 0 0 0 1px #24333d; color: #f4ead7; }
  .banner { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px 10px; background: #182832; border-bottom: 1px solid #cf9d48; }
  .eyebrow { margin: 0; color: #cf9d48; font: 700 10px/1.1 ui-monospace, "SFMono-Regular", monospace; letter-spacing: .15em; text-transform: uppercase; }
  h1 { margin: 3px 0 0; font-size: 21px; line-height: 1; font-weight: 700; letter-spacing: -.02em; }
  .status-dot { width: 9px; height: 9px; border-radius: 50%; background: #cf9d48; box-shadow: 0 0 0 3px #cf9d4830; }
  main { padding: 10px; }
  .candidate { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 10px; padding: 12px 4px; border-bottom: 1px solid #31414b; }
  .candidate:last-of-type { border-bottom: 0; }
  .candidate__rank { display: grid; place-items: start center; color: #cf9d48; font: 700 24px/1 ui-monospace, "SFMono-Regular", monospace; }
  .candidate__body { min-width: 0; }
  .candidate header { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
  code { overflow-wrap: anywhere; color: #f4ead7; font: 600 12px/1.2 ui-monospace, "SFMono-Regular", monospace; }
  .candidate header strong { flex: none; color: #cf9d48; font: 700 20px/1 ui-monospace, "SFMono-Regular", monospace; }
  .reason { margin: 8px 0 3px; overflow-wrap: anywhere; font-size: 14px; line-height: 1.3; }
  .codes { margin: 0; color: #a9c0bd; overflow-wrap: anywhere; font: 10px/1.4 ui-monospace, "SFMono-Regular", monospace; text-transform: uppercase; }
  .metrics, .components, .warnings { margin: 9px 0 0; padding: 0; }
  .metrics div, .components li { display: flex; justify-content: space-between; gap: 8px; }
  dt, .components span { color: #a9c0bd; font-size: 12px; } dd, .components strong { margin: 0; color: #f4ead7; font: 600 12px/1.2 ui-monospace, "SFMono-Regular", monospace; }
  .components { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 12px; list-style: none; }
  .warnings { padding-left: 17px; color: #ffd18a; font-size: 12px; line-height: 1.35; overflow-wrap: anywhere; }
  .provenance { display: flex; flex-wrap: wrap; gap: 4px 10px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #31414b; color: #a9c0bd; font: 10px/1.3 ui-monospace, "SFMono-Regular", monospace; overflow-wrap: anywhere; }
  .state { padding: 16px 8px; } .state h2 { margin: 0 0 6px; color: #cf9d48; font-size: 17px; } .state p { margin: 0; overflow-wrap: anywhere; font-size: 14px; line-height: 1.35; }
  .state--blocked, .state--stale, .state--unauthorized, .state--incompatible { border-left: 3px solid #cf9d48; padding-left: 11px; }
  @media (max-width: 460px) { .shell { right: 10px; bottom: 10px; width: calc(100vw - 20px); } }
`;

export class RecommendationPanel {
  private readonly root: ShadowRoot;

  constructor(target: HTMLElement = document.body) {
    const host = document.createElement("aside");
    host.setAttribute("aria-label", "NFL Fantasy Assistant recommendations");
    host.dataset.nflFantasyAssistant = "recommendations";
    this.root = host.attachShadow({ mode: "open" });
    target.append(host);
  }

  render(state: RecommendationPanelState): void {
    this.root.innerHTML = panelMarkup(state);
  }

  remove(): void {
    this.root.host.remove();
  }
}

export function panelMarkup(state: RecommendationPanelState): string {
  const current = state.kind === "current" ? "current" : state.kind;
  return `<style>${styles}</style><section class="shell" data-state="${current}"><header class="banner"><div><p class="eyebrow">Local draft companion</p><h1>Draft board</h1></div><span class="status-dot" aria-hidden="true"></span></header><main aria-live="polite">${stateMarkup(state)}</main></section>`;
}

export function stateFromApiError(error: {
  kind:
    | "authentication"
    | "conflict"
    | "incompatible"
    | "unavailable"
    | "validation";
  message: string;
  retryable: boolean;
}): RecommendationPanelState {
  const kinds: Record<
    typeof error.kind,
    "blocked" | "disconnected" | "error" | "incompatible" | "unauthorized"
  > = {
    authentication: "unauthorized",
    conflict: "blocked",
    incompatible: "incompatible",
    unavailable: "disconnected",
    validation: "error",
  };
  const kind = kinds[error.kind];
  return { kind, detail: error.message, retryable: error.retryable };
}
