/**
 * The MCP server runs validate_mece.py in whatever directory Claude Code started
 * it in, usually a user's project that has no orjson. The script imported orjson
 * with no inline dependency metadata, and the server ran it as
 * `uv run python <script>`, a form in which uv ignores inline metadata anyway, so
 * validation failed outside this repo and the tools silently skipped it.
 *
 * Once it could run, a second bug showed: the validator exits 1 when a tree is
 * invalid, execFile rejects on that, and the server reported "uv unavailable"
 * and fell back to the tree's self-reported score, so an invalid tree could
 * come back as valid.
 *
 * Both tests run the server's exact command from an empty directory. They need
 * `uv` on PATH and orjson reachable (PyPI or a warm uv cache); they skip
 * without `uv`.
 */

import { expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { runValidator, VALIDATE_SCRIPT, validatorCommand } from "./server.ts";

const hasUv = spawnSync("uv", ["--version"]).status === 0;

test.skipIf(!hasUv)("the validator runs from a directory with no project", () => {
  const cwd = fs.mkdtempSync(path.join(os.tmpdir(), "mece-validate-"));
  try {
    const input = path.join(cwd, "input.json");
    fs.writeFileSync(input, JSON.stringify({ metadata: {}, tree: {} }));
    const [cmd, args] = validatorCommand(input);
    const proc = spawnSync(cmd, args, { cwd, encoding: "utf-8", timeout: 120_000 });

    expect(proc.stderr).not.toContain("ModuleNotFoundError");
    const report = JSON.parse(proc.stdout);
    expect(report.summary).toBeDefined();
    expect(args).toContain(VALIDATE_SCRIPT);
  } finally {
    fs.rmSync(cwd, { recursive: true, force: true });
  }
});

test.skipIf(!hasUv)("an invalid tree comes back as a failing report, not an error", async () => {
  const cwd = fs.mkdtempSync(path.join(os.tmpdir(), "mece-validate-"));
  try {
    const input = path.join(cwd, "input.json");
    fs.writeFileSync(input, JSON.stringify({ metadata: {}, tree: {} }));
    const report = await runValidator(input);
    expect(report.valid).toBe(false);
    expect(report.summary.errors).toBeGreaterThan(0);
  } finally {
    fs.rmSync(cwd, { recursive: true, force: true });
  }
});
