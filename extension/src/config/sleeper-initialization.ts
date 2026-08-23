/** Explicit, extension-local pins required before a Sleeper draft can initialize. */

const MAX_TEXT_LENGTH = 256;

export interface SleeperInitializationConfiguration {
  userId: string;
  datasetVersion: string;
  featureVersion: string;
  modelVersion: string;
}

export interface ExtensionStorage {
  set(values: Record<string, unknown>): Promise<void>;
  get(key: string): Promise<Record<string, unknown>>;
}

function nonEmptyText(value: unknown): value is string {
  return (
    typeof value === "string" &&
    value.trim().length > 0 &&
    value.length <= MAX_TEXT_LENGTH
  );
}

export function validateSleeperInitializationConfiguration(
  value: SleeperInitializationConfiguration,
): SleeperInitializationConfiguration {
  if (
    !nonEmptyText(value.userId) ||
    !nonEmptyText(value.datasetVersion) ||
    !nonEmptyText(value.featureVersion) ||
    !nonEmptyText(value.modelVersion)
  ) {
    throw new Error(
      "Sleeper initialization requires an opaque user ID and pinned dataset, feature, and model versions.",
    );
  }
  return value;
}

export async function saveSleeperInitializationConfiguration(
  value: SleeperInitializationConfiguration,
  storage: ExtensionStorage = chrome.storage.local,
): Promise<void> {
  await storage.set({
    sleeperInitializationConfiguration:
      validateSleeperInitializationConfiguration(value),
  });
}

export async function loadSleeperInitializationConfiguration(
  storage: ExtensionStorage = chrome.storage.local,
): Promise<SleeperInitializationConfiguration> {
  const stored = await storage.get("sleeperInitializationConfiguration");
  const value = stored.sleeperInitializationConfiguration;
  if (
    typeof value !== "object" ||
    value === null ||
    !("userId" in value) ||
    !("datasetVersion" in value) ||
    !("featureVersion" in value) ||
    !("modelVersion" in value)
  ) {
    throw new Error(
      "Sleeper initialization is not configured in extension storage.",
    );
  }
  return validateSleeperInitializationConfiguration({
    userId: value.userId as string,
    datasetVersion: value.datasetVersion as string,
    featureVersion: value.featureVersion as string,
    modelVersion: value.modelVersion as string,
  });
}
