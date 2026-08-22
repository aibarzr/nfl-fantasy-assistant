import { readFile, readdir } from "node:fs/promises";
import { dirname, extname, join, normalize, resolve } from "node:path";

const repositoryRoot = resolve(import.meta.dirname, "..");
const markdownFiles = [];

async function collectMarkdown(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === "dist") {
      continue;
    }
    const entryPath = join(directory, entry.name);
    if (entry.isDirectory()) {
      await collectMarkdown(entryPath);
    } else if (extname(entry.name) === ".md" || entry.name === "AGENTS.md") {
      markdownFiles.push(entryPath);
    }
  }
}

function githubAnchor(heading) {
  return heading
    .toLowerCase()
    .replace(/[\[\]`*_]/g, "")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function localLinkTargets(markdown) {
  return [...markdown.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)].map((match) => match[1]);
}

await collectMarkdown(repositoryRoot);
const failures = [];

for (const markdownPath of markdownFiles) {
  const markdown = await readFile(markdownPath, "utf8");
  for (const target of localLinkTargets(markdown)) {
    if (/^(https?:|mailto:)/.test(target)) {
      continue;
    }
    const [rawPath, fragment] = target.split("#", 2);
    const targetPath = rawPath === "" ? markdownPath : resolve(dirname(markdownPath), rawPath);
    try {
      const targetMarkdown = await readFile(targetPath, "utf8");
      if (fragment !== undefined) {
        const anchors = new Set(
          [...targetMarkdown.matchAll(/^#{1,6}\s+(.+)$/gm)].map((match) => githubAnchor(match[1])),
        );
        if (!anchors.has(fragment)) {
          failures.push(`${normalize(markdownPath)}: missing anchor #${fragment} in ${target}`);
        }
      }
    } catch {
      failures.push(`${normalize(markdownPath)}: missing local link target ${target}`);
    }
  }
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`Validated ${markdownFiles.length} Markdown files and their local links.`);
}
