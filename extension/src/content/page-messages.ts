/** Validation gate for untrusted page-to-content adapter messages. */

import {
  detectEspnDraftSurface,
  ESPN_DRAFT_ORIGIN,
  type EspnSurface,
} from "../adapters/espn/surface.js";

const MAX_PAGE_MESSAGE_BYTES = 16 * 1024;
const MESSAGE_TYPE = "nfl_fantasy_assistant_espn_adapter";
const OPERATIONS = new Set([
  "initial_snapshot",
  "pick_observation",
  "adapter_diagnostic",
]);

export type PageAdapterMessage = {
  type: typeof MESSAGE_TYPE;
  operation: "initial_snapshot" | "pick_observation" | "adapter_diagnostic";
  surface: "espn_draft";
  payload: Record<string, unknown>;
};

export type PageMessageValidation =
  | { valid: true; message: PageAdapterMessage; surface: EspnSurface }
  | {
      valid: false;
      code:
        | "incompatible_surface"
        | "invalid_message_origin"
        | "invalid_message_source"
        | "invalid_message_shape"
        | "invalid_message_size"
        | "unsupported_message_operation";
      detail: string;
    };

type PageMessageEvent = Pick<
  MessageEvent<unknown>,
  "data" | "origin" | "source"
>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function encodedSize(value: unknown): number | undefined {
  try {
    return new TextEncoder().encode(JSON.stringify(value)).byteLength;
  } catch {
    return undefined;
  }
}

export function validateEspnPageMessage(
  pageUrl: string | URL,
  event: PageMessageEvent,
  expectedSource: unknown,
): PageMessageValidation {
  const detected = detectEspnDraftSurface(pageUrl);
  if (!detected.supported) {
    return {
      valid: false,
      code: "incompatible_surface",
      detail: detected.detail,
    };
  }
  if (event.origin !== ESPN_DRAFT_ORIGIN) {
    return {
      valid: false,
      code: "invalid_message_origin",
      detail:
        "The page message did not originate from the supported ESPN origin.",
    };
  }
  if (event.source !== expectedSource) {
    return {
      valid: false,
      code: "invalid_message_source",
      detail: "The page message did not come from the active page window.",
    };
  }
  const size = encodedSize(event.data);
  if (size === undefined || size > MAX_PAGE_MESSAGE_BYTES) {
    return {
      valid: false,
      code: "invalid_message_size",
      detail: "The page message exceeds the supported size limit.",
    };
  }
  if (
    !isRecord(event.data) ||
    Object.keys(event.data).length !== 4 ||
    !Object.hasOwn(event.data, "type") ||
    !Object.hasOwn(event.data, "operation") ||
    !Object.hasOwn(event.data, "surface") ||
    !Object.hasOwn(event.data, "payload") ||
    event.data.type !== MESSAGE_TYPE ||
    typeof event.data.operation !== "string" ||
    typeof event.data.surface !== "string" ||
    !isRecord(event.data.payload)
  ) {
    return {
      valid: false,
      code: "invalid_message_shape",
      detail:
        "The page message does not match the supported adapter message shape.",
    };
  }
  if (!OPERATIONS.has(event.data.operation)) {
    return {
      valid: false,
      code: "unsupported_message_operation",
      detail: "The page message operation is not supported.",
    };
  }
  if (event.data.surface !== "espn_draft") {
    return {
      valid: false,
      code: "incompatible_surface",
      detail: "The page message names an unsupported browser surface.",
    };
  }
  return {
    valid: true,
    surface: detected,
    message: event.data as PageAdapterMessage,
  };
}
