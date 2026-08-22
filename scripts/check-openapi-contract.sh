#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT
uv --directory "$root/backend" run python scripts/generate_openapi.py \
  --openapi "$temporary/openapi.json" \
  --typescript "$temporary/generated-contract.ts"
cmp --silent "$temporary/openapi.json" "$root/backend/openapi.json"
cmp --silent "$temporary/generated-contract.ts" "$root/extension/src/api/generated-contract.ts"
node --input-type=module - "$root/backend/openapi.json" "$root/extension/src/api/generated-contract.ts" <<'NODE'
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const [openapiPath, markerPath] = process.argv.slice(2);
const openapi = await readFile(openapiPath);
const marker = await readFile(markerPath, "utf8");
const hash = createHash("sha256").update(openapi).digest("hex");
if (!marker.includes(hash)) throw new Error("TypeScript contract does not match generated OpenAPI.");
for (const schema of ["DraftCreateRequest", "EventRequest", "SnapshotRequest", "ErrorEnvelope"]) {
  if (!marker.includes(`"${schema}"`)) throw new Error(`Generated TypeScript lacks ${schema}.`);
}
NODE
