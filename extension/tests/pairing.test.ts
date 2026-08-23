import { describe, expect, it } from "vitest";

import {
  savePairedBackendConfiguration,
  validatePairedBackendConfiguration,
} from "../src/config/pairing.js";
import {
  saveSleeperInitializationConfiguration,
  validateSleeperInitializationConfiguration,
} from "../src/config/sleeper-initialization.js";

const testToken = "a".repeat(43);

describe("extension pairing", () => {
  it("stores a valid token only in extension storage", async () => {
    const writes: Record<string, unknown>[] = [];
    await savePairedBackendConfiguration(
      { baseUrl: "http://127.0.0.1:8765", bearerToken: testToken },
      { set: async (value) => void writes.push(value), get: async () => ({}) },
    );

    expect(writes).toEqual([
      {
        pairedBackendConfiguration: {
          baseUrl: "http://127.0.0.1:8765",
          bearerToken: testToken,
        },
      },
    ]);
  });

  it("rejects non-loopback and mismatched configuration visibly", () => {
    expect(() =>
      validatePairedBackendConfiguration({
        baseUrl: "https://example.test",
        bearerToken: testToken,
      }),
    ).toThrow("loopback");
    expect(() =>
      validatePairedBackendConfiguration({
        baseUrl: "http://127.0.0.1:8765",
        bearerToken: "short",
      }),
    ).toThrow("missing or invalid");
    expect(() =>
      validatePairedBackendConfiguration({
        baseUrl: "http://localhost:8765",
        bearerToken: testToken,
      }),
    ).toThrow("loopback");
  });
});

describe("Sleeper initialization configuration", () => {
  it("stores only explicit opaque identity and pinned version context in extension storage", async () => {
    const writes: Record<string, unknown>[] = [];
    await saveSleeperInitializationConfiguration(
      {
        userId: "user-fixture",
        datasetVersion: "dataset-fixture",
        featureVersion: "feature-fixture",
        modelVersion: "model-fixture",
      },
      { set: async (value) => void writes.push(value), get: async () => ({}) },
    );

    expect(writes).toEqual([
      {
        sleeperInitializationConfiguration: {
          userId: "user-fixture",
          datasetVersion: "dataset-fixture",
          featureVersion: "feature-fixture",
          modelVersion: "model-fixture",
        },
      },
    ]);
  });

  it("rejects missing initialization pins before any provider read", () => {
    expect(() =>
      validateSleeperInitializationConfiguration({
        userId: "",
        datasetVersion: "dataset-fixture",
        featureVersion: "feature-fixture",
        modelVersion: "model-fixture",
      }),
    ).toThrow("opaque user ID");
  });
});
