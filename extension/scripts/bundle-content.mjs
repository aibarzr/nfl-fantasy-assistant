import { build } from "esbuild";
import { mkdir, readFile } from "node:fs/promises";

const bundles = [
  { entryPoint: "src/content/index.ts", outputFile: "dist/content/index.js" },
  { entryPoint: "src/service-worker.ts", outputFile: "dist/service-worker.js" },
];

await mkdir("dist/content", { recursive: true });
for (const { entryPoint, outputFile } of bundles) {
  await build({
    entryPoints: [entryPoint],
    bundle: true,
    format: "iife",
    legalComments: "none",
    outfile: outputFile,
    platform: "browser",
    target: ["chrome100"],
  });

  const output = await readFile(outputFile, "utf8");
  if (/^\s*(?:import|export)\b/m.test(output)) {
    throw new Error(`${entryPoint} must be bundled as a classic script`);
  }
}
