/**
 * The committed bundle is what a marketplace install runs: .mcp.json starts
 * dist/index.cjs, and the server serves dist/mcp-app.html. dist/ used to be
 * gitignored, so no install ever had a server. Now it is committed, and the
 * risk turns around: source changes that never reach the bundle.
 *
 * Each test pins one way the shipped bundle can be wrong. Fix any failure by
 * running `bun run build` in mcp-app/ and committing dist/.
 */

import { expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { sourceHash, STAMP_PATTERN } from "./build-stamp.mjs";

const DIST = path.join(import.meta.dir, "dist");
const SHIPPED = ["index.cjs", "mcp-app.html"];

test("the bundle was built from the current source", () => {
  // Stale bundle: someone edited a source file or bumped plugin.json and did
  // not rebuild. A development build carries no hash and fails here too.
  const bundle = fs.readFileSync(path.join(DIST, "index.cjs"), "utf-8");
  const stamp = bundle.match(STAMP_PATTERN)?.[1];
  expect(stamp).toBe(sourceHash());
});

test("both shipped files are tracked by git", () => {
  // The original bug: the files existed locally but a gitignore kept them out
  // of every install.
  for (const file of SHIPPED) {
    const rel = path.join("dist", file);
    const proc = spawnSync("git", ["ls-files", "--error-unmatch", rel], { cwd: import.meta.dir });
    expect(`${rel} tracked: ${proc.status === 0}`).toBe(`${rel} tracked: true`);
  }
});
