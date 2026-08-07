/**
 * Quality check logic ported from Python skill_maintainer.
 *
 * Discovers skills and plugins, runs validation checks, measures token budgets,
 * checks freshness, and verifies repo hygiene.
 */

import matter from "gray-matter";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import type {
  CheckResult,
  FileTokenEntry,
  PluginResult,
  QualityMeta,
  QualitySummary,
  RepoCheckResult,
  SkillResult,
} from "../types.js";

const SKIP_DIRS = new Set([
  "__pycache__",
  ".backup",
  "node_modules",
  ".git",
  "coderef",
  ".venv",
  "internal",
  "dist",
]);

const TOKEN_BUDGET_WARN = 4000;
const TOKEN_BUDGET_CRITICAL = 8000;
const STALE_DAYS = 30;

const PLUGIN_REQUIRED_FIELDS = [
  "name",
  "version",
  "description",
  "author",
  "repository",
];

// Allowed top-level fields in SKILL.md frontmatter (Agent Skills spec)
const ALLOWED_FIELDS = new Set([
  "name",
  "description",
  "metadata",
]);

// ============================================================================
// Discovery
// ============================================================================

function shouldSkip(filePath: string): boolean {
  const parts = filePath.split(path.sep);
  return parts.some((p) => SKIP_DIRS.has(p));
}

// Relative path prefixes never scanned, matched as whole components against
// the path relative to the walk's own root -- not the absolute path, so a
// checkout that happens to sit under a directory named "worktrees" elsewhere
// on disk isn't affected.
//
// `.claude/worktrees/` is where Claude Code puts a git worktree for
// `isolation: worktree` and `EnterWorktree`. A worktree is a second checkout
// of the same repo, so scanning it doubles every plugin. See
// tools/skill-maintainer/src/skill_maintainer/shared.py's SKIP_PATH_PREFIXES
// for the specimen this mirrors (265/3 -> 499/6 on `skill-maintain test`).
const SKIP_PATH_PREFIXES: string[][] = [[".claude", "worktrees"]];

function isSkippedPrefix(relParts: string[]): boolean {
  return SKIP_PATH_PREFIXES.some(
    (prefix) =>
      prefix.length <= relParts.length &&
      prefix.every((part, i) => relParts[i] === part),
  );
}

function walkDir(
  dir: string,
  pattern: RegExp,
  opts?: { enterDotDirs?: boolean },
): string[] {
  const results: string[] = [];
  if (!fs.existsSync(dir)) return results;
  const enterDot = opts?.enterDotDirs ?? false;

  function walk(current: string) {
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) continue;
        if (!enterDot && entry.name.startsWith(".")) continue;
        if (isSkippedPrefix(path.relative(dir, fullPath).split(path.sep))) continue;
        walk(fullPath);
      } else if (pattern.test(entry.name)) {
        results.push(fullPath);
      }
    }
  }

  walk(dir);
  return results.sort();
}

export function discoverSkills(root: string): string[] {
  return walkDir(root, /^SKILL\.md$/)
    .filter((p) => !shouldSkip(p))
    .map((p) => path.dirname(p));
}

// Directories whose package.json belongs to someone else: node_modules holds
// thousands of foreign versions, dist/build hold bundler copies of our own.
// walkDir already skips node_modules and dist; `build` is named here so this
// matches skill-maintainer's _PACKAGE_JSON_SKIP rather than quietly diverging
// from the Python check it is supposed to agree with.
const PACKAGE_JSON_SKIP = new Set(["node_modules", "dist", "build", ".backup"]);

/**
 * Authored package.json versions under a plugin, keyed by path relative to it.
 *
 * Returns nothing for a package.json with no `version` key. That is the shape
 * the MCP apps ship on purpose -- the field has no consumer, so it was deleted
 * rather than maintained -- and a copy that does not exist cannot drift.
 */
function authoredPackageVersions(pluginDir: string): [string, string][] {
  const out: [string, string][] = [];
  for (const p of walkDir(pluginDir, /^package\.json$/)) {
    const rel = path.relative(pluginDir, p);
    if (rel.split(path.sep).some((part) => PACKAGE_JSON_SKIP.has(part))) continue;
    try {
      const version = JSON.parse(fs.readFileSync(p, "utf-8")).version;
      if (typeof version === "string") out.push([rel, version]);
    } catch {
      // Unreadable is a finding, not a skip: staying silent about a file this
      // check cannot parse reports green for a copy whose state is unknown.
      out.push([rel, "unreadable"]);
    }
  }
  return out;
}

export function discoverPlugins(root: string): string[] {
  return walkDir(root, /^plugin\.json$/, { enterDotDirs: true })
    .filter((p) => {
      if (shouldSkip(p)) return false;
      // Must be inside .claude-plugin/
      const dir = path.dirname(p);
      if (path.basename(dir) !== ".claude-plugin") return false;
      // Skip the root marketplace
      const pluginDir = path.dirname(dir);
      if (pluginDir === root) return false;
      return true;
    })
    .map((p) => path.dirname(path.dirname(p)));
}

// ============================================================================
// Spec validation (ported from skills-ref Python validator)
// ============================================================================

function isKebabCase(name: string): boolean {
  return /^[a-z0-9]+(-[a-z0-9]+)*$/.test(name);
}

interface SpecErrors {
  errors: string[];
}

function validateSpec(
  skillDir: string,
  frontmatter: Record<string, unknown>,
): SpecErrors {
  const errors: string[] = [];
  const dirName = path.basename(skillDir);

  const name = frontmatter.name;
  if (!name || typeof name !== "string") {
    errors.push("missing required field: name");
  } else {
    if (!isKebabCase(name)) {
      errors.push(`name '${name}' is not kebab-case`);
    }
    if (name !== dirName) {
      errors.push(`name '${name}' does not match directory '${dirName}'`);
    }
  }

  const desc = frontmatter.description;
  if (!desc || typeof desc !== "string") {
    errors.push("missing required field: description");
  } else {
    if (desc.length > 1024) {
      errors.push(`description is ${desc.length} chars (max 1024)`);
    }
    if (/<[^>]+>/.test(desc)) {
      errors.push("description contains angle brackets");
    }
  }

  // Check for disallowed top-level fields
  for (const key of Object.keys(frontmatter)) {
    if (!ALLOWED_FIELDS.has(key)) {
      errors.push(`disallowed top-level field: ${key}`);
    }
  }

  return { errors };
}

// ============================================================================
// Token measurement
// ============================================================================

export function measureTokensDetailed(skillDir: string): FileTokenEntry[] {
  const skipSet = new Set([...SKIP_DIRS, "state"]);
  const files: { path: string; chars: number }[] = [];

  function walk(dir: string) {
    if (!fs.existsSync(dir)) return;
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name.startsWith(".")) continue;
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (!skipSet.has(entry.name)) walk(fullPath);
      } else if (entry.name.endsWith(".md")) {
        try {
          const chars = fs.readFileSync(fullPath, "utf-8").length;
          files.push({ path: path.relative(skillDir, fullPath), chars });
        } catch {
          // skip unreadable files
        }
      }
    }
  }

  walk(skillDir);

  const totalChars = files.reduce((sum, f) => sum + f.chars, 0);

  return files
    .map((f) => ({
      path: f.path,
      chars: f.chars,
      tokens: Math.floor(f.chars / 4),
      pctOfTotal: totalChars > 0 ? Math.round((f.chars / totalChars) * 100) : 0,
    }))
    .sort((a, b) => b.tokens - a.tokens);
}

function measureTokens(skillDir: string): number {
  return measureTokensDetailed(skillDir).reduce((sum, f) => sum + f.tokens, 0);
}

export function findSkillPath(root: string, skillName: string): string | null {
  const dirs = discoverSkills(root);
  const match = dirs.find((d) => path.basename(d) === skillName);
  return match ? path.join(match, "SKILL.md") : null;
}

// ============================================================================
// Freshness
// ============================================================================

function daysSince(dateStr: string): number | null {
  try {
    const d = new Date(dateStr + "T00:00:00Z");
    if (isNaN(d.getTime())) return null;
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

// ============================================================================
// Description quality
// ============================================================================

function checkDescriptionQuality(description: string): string[] {
  const issues: string[] = [];
  if (!description) return ["no description"];

  const lower = description.toLowerCase();
  const hasWhat = [
    "use when",
    "use for",
    "handles",
    "manages",
    "creates",
    "generates",
    "monitors",
    "validates",
    "analyzes",
    "design",
  ].some((w) => lower.includes(w));

  const hasWhen = [
    "use when",
    "when user",
    "when the",
    "if user",
    "trigger",
    "mention",
    "says",
  ].some((w) => lower.includes(w));

  if (!hasWhat) issues.push("missing WHAT verb");
  if (!hasWhen) issues.push("missing WHEN trigger");
  return issues;
}

// ============================================================================
// Skill checks
// ============================================================================

export function checkSkills(
  root: string,
  filter?: string,
): SkillResult[] {
  const skillDirs = discoverSkills(root);
  const results: SkillResult[] = [];

  for (const skillDir of skillDirs) {
    const name = path.basename(skillDir);
    if (filter && !name.includes(filter)) continue;

    const skillMdPath = path.join(skillDir, "SKILL.md");
    if (!fs.existsSync(skillMdPath)) continue;

    let content: string;
    try {
      content = fs.readFileSync(skillMdPath, "utf-8");
    } catch {
      continue;
    }

    // Parse frontmatter
    let frontmatter: Record<string, unknown>;
    let body: string;
    try {
      const parsed = matter(content);
      frontmatter = parsed.data as Record<string, unknown>;
      body = parsed.content;
    } catch {
      results.push({
        name,
        checks: {
          specCompliance: {
            name: "spec compliance",
            passed: false,
            detail: "failed to parse frontmatter",
          },
          tokenBudget: {
            name: "token budget",
            passed: false,
            detail: "skipped",
          },
          bodySize: { name: "body size", passed: false, detail: "skipped" },
          staleness: { name: "staleness", passed: false, detail: "skipped" },
          descriptionQuality: {
            name: "description quality",
            passed: false,
            detail: "skipped",
          },
        },
      });
      continue;
    }

    // 1. Spec compliance
    const spec = validateSpec(skillDir, frontmatter);
    const specCheck: CheckResult = {
      name: "spec compliance",
      passed: spec.errors.length === 0,
      detail: spec.errors.length > 0 ? spec.errors.join("; ") : "",
    };

    // 2. Token budget
    const tokens = measureTokens(skillDir);
    const budgetPassed = tokens < TOKEN_BUDGET_WARN;
    let budgetDetail = tokens.toLocaleString();
    if (!budgetPassed) {
      budgetDetail =
        tokens >= TOKEN_BUDGET_CRITICAL
          ? `${tokens.toLocaleString()} > ${TOKEN_BUDGET_CRITICAL.toLocaleString()}`
          : `${tokens.toLocaleString()} > ${TOKEN_BUDGET_WARN.toLocaleString()}`;
    }
    const budgetCheck: CheckResult = {
      name: "token budget",
      passed: budgetPassed,
      detail: budgetDetail,
    };

    // 3. Body size
    const lineCount = body.trim().split("\n").length;
    const bodySizeCheck: CheckResult = {
      name: "body size",
      passed: lineCount <= 500,
      detail:
        lineCount <= 500
          ? `${lineCount} lines`
          : `${lineCount} lines > 500`,
    };

    // 4. Staleness
    const meta =
      typeof frontmatter.metadata === "object" && frontmatter.metadata !== null
        ? (frontmatter.metadata as Record<string, unknown>)
        : {};
    const lastVerified = meta.last_verified;
    let stalenessCheck: CheckResult;
    if (lastVerified && typeof lastVerified === "string") {
      const days = daysSince(lastVerified);
      if (days !== null) {
        stalenessCheck = {
          name: "staleness",
          passed: days <= STALE_DAYS,
          detail:
            days <= STALE_DAYS
              ? `${days}d`
              : `${days}d > ${STALE_DAYS}d`,
        };
      } else {
        stalenessCheck = {
          name: "staleness",
          passed: false,
          detail: `invalid date: ${lastVerified}`,
        };
      }
    } else if (lastVerified instanceof Date) {
      const lvStr = lastVerified.toISOString().slice(0, 10);
      const days = daysSince(lvStr);
      if (days !== null) {
        stalenessCheck = {
          name: "staleness",
          passed: days <= STALE_DAYS,
          detail: days <= STALE_DAYS ? `${days}d` : `${days}d > ${STALE_DAYS}d`,
        };
      } else {
        stalenessCheck = {
          name: "staleness",
          passed: false,
          detail: "unparseable date",
        };
      }
    } else {
      stalenessCheck = {
        name: "staleness",
        passed: false,
        detail: "missing metadata.last_verified",
      };
    }

    // 5. Description quality
    const description =
      typeof frontmatter.description === "string"
        ? frontmatter.description
        : "";
    const descIssues = checkDescriptionQuality(description);
    const descCheck: CheckResult = {
      name: "description quality",
      passed: descIssues.length === 0,
      detail: descIssues.length > 0 ? descIssues.join("; ") : "",
    };

    results.push({
      name,
      checks: {
        specCompliance: specCheck,
        tokenBudget: budgetCheck,
        bodySize: bodySizeCheck,
        staleness: stalenessCheck,
        descriptionQuality: descCheck,
      },
    });
  }

  return results;
}

// ============================================================================
// Plugin checks
// ============================================================================

function loadMarketplaceNames(root: string): string[] {
  const mpPath = path.join(root, ".claude-plugin", "marketplace.json");
  if (!fs.existsSync(mpPath)) return [];
  try {
    const data = JSON.parse(fs.readFileSync(mpPath, "utf-8"));
    return (data.plugins || []).map(
      (p: { name: string }) => p.name,
    );
  } catch {
    return [];
  }
}

function loadMarketplaceVersions(root: string): Record<string, string> {
  const mpPath = path.join(root, ".claude-plugin", "marketplace.json");
  if (!fs.existsSync(mpPath)) return {};
  try {
    const data = JSON.parse(fs.readFileSync(mpPath, "utf-8"));
    const result: Record<string, string> = {};
    for (const p of data.plugins || []) {
      if (p.name && p.version) result[p.name] = p.version;
    }
    return result;
  } catch {
    return {};
  }
}

export function checkPlugins(root: string): PluginResult[] {
  const pluginDirs = discoverPlugins(root);
  const marketplaceNames = loadMarketplaceNames(root);
  const results: PluginResult[] = [];

  for (const pluginDir of pluginDirs) {
    const name = path.basename(pluginDir);
    const manifestPath = path.join(
      pluginDir,
      ".claude-plugin",
      "plugin.json",
    );

    let manifest: Record<string, unknown>;
    try {
      manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
    } catch (e) {
      results.push({
        name,
        checks: {
          manifestFields: {
            name: "manifest fields",
            passed: false,
            detail: `cannot read: ${e instanceof Error ? e.message : String(e)}`,
          },
          marketplaceListing: {
            name: "marketplace listing",
            passed: false,
            detail: "skipped (no manifest)",
          },
          readmeExists: {
            name: "README exists",
            passed: false,
            detail: "skipped (no manifest)",
          },
        },
      });
      continue;
    }

    // 1. Manifest fields
    const missing = PLUGIN_REQUIRED_FIELDS.filter(
      (f) => !manifest[f],
    );
    const manifestCheck: CheckResult = {
      name: "manifest fields",
      passed: missing.length === 0,
      detail:
        missing.length > 0 ? `missing: ${missing.join(", ")}` : "",
    };

    // 2. Marketplace listing
    const inMarketplace = marketplaceNames.includes(name);
    const marketplaceCheck: CheckResult = {
      name: "marketplace listing",
      passed: marketplaceNames.length === 0 || inMarketplace,
      detail: inMarketplace ? "" : "not in marketplace.json",
    };

    // 3. README exists
    const readmePath = path.join(pluginDir, "README.md");
    const hasReadme = fs.existsSync(readmePath);
    const readmeCheck: CheckResult = {
      name: "README exists",
      passed: hasReadme,
      detail: hasReadme ? "" : "missing README.md",
    };

    results.push({
      name,
      checks: {
        manifestFields: manifestCheck,
        marketplaceListing: marketplaceCheck,
        readmeExists: readmeCheck,
      },
    });
  }

  return results;
}

// ============================================================================
// best_practices.md provenance join (ported from skill_maintainer.provenance)
// ============================================================================
//
// Replaces a `last updated within STALE_DAYS` check on best_practices.md's
// first line, which established only that someone had edited the file, not
// that anyone had checked it against its source. See provenance.py in
// tools/skill-maintainer for the incident that motivated the replacement.

interface Annotation {
  section: string;
  evidenceClass: string;
  source: string | null;
  verifiedHash: string | null;
  lastVerified: string | null;
}

interface Finding {
  section: string;
  source: string;
  verifiedHash: string | null;
  currentHash: string | null;
  lastVerified: string | null;
}

interface JoinResult {
  moved: Finding[];
  current: Finding[];
  unbound: Finding[];
  untracked: Finding[];
  unattributed: string[];
}

const HEADING_RE = /^#{2,3}\s+(.*?)\s*$/gm;
// `s` (dotAll) so a comment wrapped across lines still matches -- matched
// against a whole section span (see parseAnnotations), not a single line.
const ANNOTATION_RE = /<!--\s*(class:.*?)\s*-->/gs;

function parseFields(blob: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const part of blob.split("|")) {
    const idx = part.indexOf(":");
    if (idx === -1) continue;
    out[part.slice(0, idx).trim()] = part.slice(idx + 1).trim();
  }
  return out;
}

function parseAnnotations(text: string): Annotation[] {
  const spans: [string, string][] = [];
  let prevEnd = 0;
  let prevSection = "";
  HEADING_RE.lastIndex = 0;
  let h: RegExpExecArray | null;
  while ((h = HEADING_RE.exec(text)) !== null) {
    spans.push([prevSection, text.slice(prevEnd, h.index)]);
    prevSection = h[1];
    prevEnd = HEADING_RE.lastIndex;
  }
  spans.push([prevSection, text.slice(prevEnd)]);

  const annotations: Annotation[] = [];
  for (const [section, chunk] of spans) {
    ANNOTATION_RE.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = ANNOTATION_RE.exec(chunk)) !== null) {
      const fields = parseFields(m[1]);
      annotations.push({
        section,
        evidenceClass: fields["class"] ?? "",
        source: fields["source"] ?? null,
        verifiedHash: fields["verified_hash"] ?? null,
        lastVerified: fields["last_verified"] ?? null,
      });
    }
  }
  return annotations;
}

function joinProvenance(
  annotations: Annotation[],
  tracked: Record<string, string>,
  repos: Record<string, string>,
): JoinResult {
  const trackedPages: Record<string, string> = {};
  for (const [u, hash] of Object.entries(tracked)) {
    if (u.startsWith("http://") || u.startsWith("https://")) trackedPages[u] = hash;
  }

  const result: JoinResult = {
    moved: [],
    current: [],
    unbound: [],
    untracked: [],
    unattributed: [],
  };
  const cited = new Set<string>();

  for (const ann of annotations) {
    if (ann.evidenceClass !== "harness" || !ann.source) continue;

    let current: string;
    let prefixMatch: boolean;
    if (ann.source in trackedPages) {
      current = trackedPages[ann.source];
      prefixMatch = false;
    } else if (ann.source in repos) {
      current = repos[ann.source];
      prefixMatch = true;
    } else {
      result.untracked.push({
        section: ann.section,
        source: ann.source,
        verifiedHash: ann.verifiedHash,
        currentHash: null,
        lastVerified: ann.lastVerified,
      });
      continue;
    }

    cited.add(ann.source);
    const finding: Finding = {
      section: ann.section,
      source: ann.source,
      verifiedHash: ann.verifiedHash,
      currentHash: current,
      lastVerified: ann.lastVerified,
    };
    // Falsy, not just non-null: an annotation with a present-but-blank
    // verified_hash must not read as verified via a vacuous prefix match.
    if (!ann.verifiedHash) {
      result.unbound.push(finding);
      continue;
    }
    const matches = prefixMatch
      ? current.startsWith(ann.verifiedHash)
      : current === ann.verifiedHash;
    (matches ? result.current : result.moved).push(finding);
  }

  result.unattributed = Object.keys(trackedPages)
    .filter((u) => !cited.has(u))
    .sort();
  return result;
}

function loadHashState(root: string): Record<string, unknown> {
  const p = path.join(root, ".skill-maintainer", "state", "upstream_hashes.json");
  if (!fs.existsSync(p)) return {};
  try {
    return JSON.parse(fs.readFileSync(p, "utf-8"));
  } catch {
    return {};
  }
}

// ============================================================================
// Repo hygiene
// ============================================================================

export function checkRepoHygiene(root: string): RepoCheckResult[] {
  const results: RepoCheckResult[] = [];

  // 1. No blanket .claude/ gitignore
  const gitignorePath = path.join(root, ".gitignore");
  let blanketFound = false;
  if (fs.existsSync(gitignorePath)) {
    const lines = fs.readFileSync(gitignorePath, "utf-8").split("\n");
    blanketFound = lines.some((line) => {
      const stripped = line.trim();
      return stripped === ".claude/" || stripped === ".claude";
    });
  }
  results.push({
    check: "no blanket .claude/ gitignore",
    passed: !blanketFound,
    detail: blanketFound ? "found blanket .claude/ ignore rule" : "",
  });

  // 2. No broad ambient hooks
  const settingsPath = path.join(root, ".claude", "settings.json");
  const broadHooks: string[] = [];
  const highFreqEvents = new Set(["PreToolUse", "PostToolUse"]);
  if (fs.existsSync(settingsPath)) {
    try {
      const settings = JSON.parse(
        fs.readFileSync(settingsPath, "utf-8"),
      );
      const hooks = settings.hooks || {};
      for (const [eventName, hookList] of Object.entries(hooks)) {
        if (!highFreqEvents.has(eventName)) continue;
        if (!Array.isArray(hookList)) continue;
        for (const hook of hookList) {
          if (
            typeof hook === "object" &&
            hook !== null &&
            !("matcher" in hook)
          ) {
            broadHooks.push(`${eventName} (no matcher)`);
          }
        }
      }
    } catch {
      // skip unparseable settings
    }
  }
  results.push({
    check: "no broad ambient hooks",
    passed: broadHooks.length === 0,
    detail: broadHooks.length > 0 ? broadHooks.join("; ") : "",
  });

  // 3. State files gitignored
  const statePatterns = [".skill-maintainer/state/"];
  const notIgnored: string[] = [];
  for (const pattern of statePatterns) {
    try {
      execFileSync("git", ["check-ignore", "-q", pattern], {
        cwd: root,
        stdio: "pipe",
      });
    } catch {
      notIgnored.push(pattern);
    }
  }
  results.push({
    check: "state files gitignored",
    passed: notIgnored.length === 0,
    detail:
      notIgnored.length > 0
        ? `not ignored: ${notIgnored.join(", ")}`
        : "",
  });

  // 4. No duplicate skill names
  const skills = discoverSkills(root);
  const names = skills.map((s) => path.basename(s));
  const seen = new Set<string>();
  const dupes = new Set<string>();
  for (const n of names) {
    if (seen.has(n)) dupes.add(n);
    seen.add(n);
  }
  results.push({
    check: "no duplicate skill names",
    passed: dupes.size === 0,
    detail:
      dupes.size > 0
        ? `duplicates: ${[...dupes].sort().join(", ")}`
        : "",
  });

  // 5. best_practices.md provenance. Two arms, because a hash-only join lies
  // on its own: it reads STORED hashes, so it reports a comfortable zero when
  // nobody has fetched in months. The join says what to conclude; the date
  // says when to go look.
  const bpPath = path.join(root, ".skill-maintainer", "best_practices.md");
  if (fs.existsSync(bpPath)) {
    const content = fs.readFileSync(bpPath, "utf-8");
    const state = loadHashState(root);
    const tracked: Record<string, string> = {};
    for (const [u, hash] of Object.entries(state)) {
      if (typeof hash === "string") tracked[u] = hash;
    }
    const repos: Record<string, string> =
      typeof state.local_repos === "object" && state.local_repos !== null
        ? (state.local_repos as Record<string, string>)
        : {};
    const join = joinProvenance(parseAnnotations(content), tracked, repos);
    const harnessSections =
      join.moved.length + join.current.length + join.unbound.length + join.untracked.length;
    const scope =
      `${harnessSections} harness annotations: ${join.current.length} current, ` +
      `${join.unbound.length} unbound, ${join.untracked.length} untracked source`;
    results.push({
      check: "best_practices provenance",
      passed: join.moved.length === 0,
      detail:
        join.moved.length === 0
          ? scope
          : `${join.moved.length} moved: ` +
            join.moved.map((f) => `${f.section} (${f.source.split("/").pop()})`).join(", "),
    });

    const hashesPath = path.join(root, ".skill-maintainer", "state", "upstream_hashes.json");
    if (fs.existsSync(hashesPath)) {
      const mtimeStr = fs.statSync(hashesPath).mtime.toISOString().slice(0, 10);
      const age = daysSince(mtimeStr) ?? Number.MAX_SAFE_INTEGER;
      results.push({
        check: "upstream hash state fresh",
        passed: age <= STALE_DAYS,
        detail:
          age <= STALE_DAYS
            ? `fetched ${age}d ago`
            : `fetched ${age}d ago > ${STALE_DAYS}d -- run \`skill-maintain upstream\``,
      });
    } else {
      results.push({
        check: "upstream hash state fresh",
        passed: false,
        detail: "no upstream_hashes.json -- the provenance join has nothing to compare against",
      });
    }
  }

  // 6. Version alignment across plugin.json, marketplace.json, pyproject.toml,
  //    and any authored package.json.
  //
  //    SKILL.md's metadata.version used to be read here. It is a removed class
  //    -- the version cascade deliberately excludes SKILL.md -- so the branch
  //    could only ever fire on a field that is not supposed to exist, reporting
  //    "drift" whose correct fix is deleting the field it read.
  const pluginDirs = discoverPlugins(root);
  const marketplaceVersions = loadMarketplaceVersions(root);
  const misaligned: string[] = [];

  for (const pluginDir of pluginDirs) {
    const name = path.basename(pluginDir);
    const versions: Record<string, string> = {};

    // plugin.json version
    const manifestPath = path.join(pluginDir, ".claude-plugin", "plugin.json");
    try {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
      if (manifest.version) versions["plugin.json"] = manifest.version;
    } catch { /* skip */ }

    // marketplace.json version
    const mpVersion = marketplaceVersions[name];
    if (mpVersion) versions["marketplace"] = mpVersion;

    // Any authored package.json. Unlike the others this copy has no consumer
    // -- nothing imports it, no build reads it -- so absent is the correct
    // state and only a version that exists and disagrees is a finding. Both
    // MCP-App plugins had one drift silently before this was checked.
    for (const [rel, ver] of authoredPackageVersions(pluginDir)) {
      versions[rel] = ver;
    }

    // pyproject.toml version (if exists at plugin root)
    const pyprojectPath = path.join(pluginDir, "pyproject.toml");
    if (fs.existsSync(pyprojectPath)) {
      try {
        const pyContent = fs.readFileSync(pyprojectPath, "utf-8");
        const vMatch = pyContent.match(/^version\s*=\s*"([^"]+)"/m);
        if (vMatch) versions["pyproject"] = vMatch[1];
      } catch { /* skip */ }
    }

    // Check if all versions agree
    const uniqueVersions = new Set(Object.values(versions));
    if (uniqueVersions.size > 1) {
      const detail = Object.entries(versions)
        .map(([src, ver]) => `${src}=${ver}`)
        .join(", ");
      misaligned.push(`${name}: ${detail}`);
    }
  }

  results.push({
    check: "version alignment",
    passed: misaligned.length === 0,
    detail:
      misaligned.length > 0
        ? misaligned.join("; ")
        : "",
  });

  return results;
}

// ============================================================================
// Main entry point
// ============================================================================

export function runQualityCheck(
  root: string,
  filter?: string,
): {
  skills: SkillResult[];
  plugins: PluginResult[];
  repo: RepoCheckResult[];
  summary: QualitySummary;
  meta: QualityMeta;
} {
  const skills = checkSkills(root, filter);
  const plugins = checkPlugins(root);
  const repo = checkRepoHygiene(root);

  // Count pass/fail across all checks
  let passed = 0;
  let failed = 0;

  for (const s of skills) {
    for (const c of Object.values(s.checks)) {
      if (c.passed) passed++;
      else failed++;
    }
  }
  for (const p of plugins) {
    for (const c of Object.values(p.checks)) {
      if (c.passed) passed++;
      else failed++;
    }
  }
  for (const r of repo) {
    if (r.passed) passed++;
    else failed++;
  }

  return {
    skills,
    plugins,
    repo,
    summary: { passed, failed, total: passed + failed },
    meta: {
      generatedAt: new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC",
      budgetWarn: TOKEN_BUDGET_WARN,
      budgetCritical: TOKEN_BUDGET_CRITICAL,
    },
  };
}
