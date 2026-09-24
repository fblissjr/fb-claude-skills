// The committed bundle (dist/index.cjs, dist/mcp-app.html) is what a marketplace
// install runs, so it must match the source. build-server.mjs writes this stamp
// into the bundle's banner; bundle.test.ts recomputes it and fails when they
// differ. Both import this module, so they cannot hash differently.

import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const HERE = path.dirname(new URL(import.meta.url).pathname);

// Everything the build reads: the app's own files and the plugin manifest,
// whose version vite.config.ts injects into the UI. Tests, build output and
// installed packages are not inputs (bun.lock pins the packages).
const SKIP_DIRS = new Set(["node_modules", "dist", ".claude"]);
const SKIP_FILE = (name) => name.endsWith(".test.ts") || name === ".gitignore" || name === ".DS_Store";

function inputFiles(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.has(entry.name)) out.push(...inputFiles(path.join(dir, entry.name)));
    } else if (!SKIP_FILE(entry.name)) {
      out.push(path.join(dir, entry.name));
    }
  }
  return out;
}

/** Hex SHA-256 over the build inputs, stable across machines. */
export function sourceHash() {
  const files = [...inputFiles(HERE), path.join(HERE, "..", ".claude-plugin", "plugin.json")];
  const hash = createHash("sha256");
  for (const file of files.map((f) => path.relative(HERE, f)).sort()) {
    hash.update(file.split(path.sep).join("/"));
    hash.update("\0");
    hash.update(fs.readFileSync(path.join(HERE, file)));
    hash.update("\0");
  }
  return hash.digest("hex");
}

/** The banner line. A development build is stamped so it can never pass as current. */
export function stampLine(mode) {
  return `// mece-build-stamp: ${mode === "production" ? sourceHash() : "development-build"}`;
}

export const STAMP_PATTERN = /^\/\/ mece-build-stamp: (\S+)$/m;
