const TOKEN_PATTERN = /^[A-Za-z0-9_-]{43,}$/;

export interface PairedBackendConfiguration {
  baseUrl: string;
  bearerToken: string;
}

export interface ExtensionStorage {
  set(values: Record<string, unknown>): Promise<void>;
  get(key: string): Promise<Record<string, unknown>>;
}

export function validatePairedBackendConfiguration(
  value: PairedBackendConfiguration,
): PairedBackendConfiguration {
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(value.baseUrl);
  } catch {
    throw new Error("The backend URL must be a valid loopback HTTP URL.");
  }

  if (parsedUrl.protocol !== "http:" || parsedUrl.hostname !== "127.0.0.1") {
    throw new Error("The backend URL must target a local loopback address.");
  }
  if (!TOKEN_PATTERN.test(value.bearerToken)) {
    throw new Error(
      "The pairing token is missing or invalid. Pair the extension again.",
    );
  }
  return value;
}

export async function savePairedBackendConfiguration(
  value: PairedBackendConfiguration,
  storage: ExtensionStorage = chrome.storage.local,
): Promise<void> {
  await storage.set({
    pairedBackendConfiguration: validatePairedBackendConfiguration(value),
  });
}

export async function loadPairedBackendConfiguration(
  storage: ExtensionStorage = chrome.storage.local,
): Promise<PairedBackendConfiguration> {
  const stored = await storage.get("pairedBackendConfiguration");
  const value = stored.pairedBackendConfiguration;
  if (
    typeof value !== "object" ||
    value === null ||
    !("baseUrl" in value) ||
    !("bearerToken" in value) ||
    typeof value.baseUrl !== "string" ||
    typeof value.bearerToken !== "string"
  ) {
    throw new Error(
      "The extension is not paired. Pair it from service-worker tools.",
    );
  }
  return validatePairedBackendConfiguration({
    baseUrl: value.baseUrl,
    bearerToken: value.bearerToken,
  });
}
