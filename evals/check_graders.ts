// Offline fallibility check for the regex and tool_used graders.
// Every grader must compile as a JS regex; every not_contains grader must go RED on
// the original draft (it can fail), and every grader must go GREEN on a compliant
// hand-written rewrite (it can pass). tool_used patterns are checked against the
// JSON-encoded Skill inputs the CLI matches.
import { readdirSync, readFileSync, existsSync } from "fs";
import { join } from "path";

const repo = process.argv[2];

function fm(path: string): { data: any; body: string } {
  const txt = readFileSync(path, "utf8");
  const m = txt.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) throw new Error(`no frontmatter: ${path}`);
  return { data: Bun.YAML.parse(m[1]) ?? {}, body: m[2] };
}

function regexPass(g: any, text: string): boolean {
  const re = new RegExp(g.pattern, (g.flags ?? "") + "g");
  const n = [...text.matchAll(re)].length;
  const match = g.match ?? "contains";
  if (match === "not_contains") return n === 0;
  if (match.startsWith("count:")) return n === Number(match.slice(6));
  return n > 0;
}

const GREEN: Record<string, string> = {
  "status-update-rewrite": `# Q3 checkout latency: results and next steps

We cut checkout p95 latency from 820 ms to 310 ms this quarter.

## What changed

- The connection pool changes did the most work.
- The new caching layer removed redundant database round-trips.

## Next

In Q4 we will go after the remaining latency, starting with the payment-provider call.`,
  "oncall-guide-american-usage": `## Before your first shift

Learn how the paging system escalates, prioritizes, and routes alerts. By the end of your first week, organize a shadow shift with a senior engineer, for example someone from the platform or database team.

## When an alert fires

1. Acknowledge the page within 5 minutes, even if you do not know what is wrong yet.
2. Open the runbook linked in the alert.
3. Analyze the dashboard.
4. Post a short update in the incident channel.`,
  "incident-summary-front-load": `An expired TLS certificate on the internal auth proxy caused about 40% of sign-in attempts to fail for two hours on Tuesday.

The on-call engineer got the alert at 09:14. We first suspected the morning deploy and rolled it back, but the errors continued. At 11:02 we found the expired certificate. We renewed it and restored service at 11:20.

We will add a monitor for certificate expiry.`,
  "check-mode-names-violations": `1. Heading: "Why We Moved Off The Old Scheduler" is Title Case. Use sentence case.
2. Em dash: "was — to put it mildly —" uses em dashes. Use commas.
3. Bold: **unreliable** is bold for emphasis. Remove it.
4. Machine register: "It is important to note" is filler.`,
  "no-trigger-grammar-question": `A gerund is a verb form ending in -ing used as a noun ("swimming is fun"). A nominalization turns a verb or adjective into a noun ("decide" to "decision").`,
  "show-me-call-structure": "```\nhandler\n├── validate()\n│   ├── load_schema()\n│   └── check_types()\n└── save()\n    ├── serialize()\n    └── write_row()\n        └── with_backoff()\n```",
};

let failures = 0;
const say = (ok: boolean, msg: string) => {
  if (!ok) failures++;
  console.log(`${ok ? "ok  " : "FAIL"} ${msg}`);
};

// --- writing suite: regex graders, red on draft, green on rewrite
const wdir = join(repo, "skills/writing/evals");
for (const c of readdirSync(wdir).sort()) {
  const p = join(wdir, c, "prompt.md");
  if (!existsSync(p)) continue;
  const draft = fm(p).body.trim().split(/\n\n/).slice(1).join("\n\n");
  for (const gf of readdirSync(join(wdir, c, "graders")).sort()) {
    const g = fm(join(wdir, c, "graders", gf)).data;
    const id = `${c}/${gf}`;
    if (g.type === "regex") {
      try { new RegExp(g.pattern, g.flags ?? ""); } catch (e) { say(false, `${id} does not compile: ${e}`); continue; }
      if ((g.match ?? "contains") === "not_contains") say(!regexPass(g, draft), `${id} goes red on the draft`);
      if (GREEN[c] !== undefined) say(regexPass(g, GREEN[c]), `${id} goes green on a compliant reply`);
    } else if (g.type === "tool_used") {
      const re = new RegExp(g.input_match);
      const skill = g.input_match.match(/\)\?([\w-]+)"$/)?.[1];
      for (const inp of [{ skill: `writing:${skill}` }, { skill, args: "edit" }]) say(re.test(JSON.stringify(inp)), `${id} matches ${JSON.stringify(inp)}`);
      for (const other of ["plain-language-us", "voice-match", "show-me", "wait-what"].filter((s) => s !== skill)) {
        say(!re.test(JSON.stringify({ skill: `writing:${other}` })), `${id} does not match writing:${other}`);
      }
    }
  }
}

// --- routing suite: each case's positive pattern matches exactly its route; the
// negative alternation matches exactly the other family members (and never the route).
const FAMILY = ["postmortem", "test-audit", "control-audit", "adversarial-verify", "postmortem-index", "claim-audit"];
const plugOf = (s: string) => (s === "claim-audit" ? "claim-audit" : "postmortem");
const rdir = join(repo, "evals/verification-routing");
for (const c of readdirSync(rdir).sort()) {
  const gd = join(rdir, c, "graders");
  if (!existsSync(gd)) continue;
  const tag = fm(join(rdir, c, "prompt.md")).data.tags[1];
  for (const gf of readdirSync(gd).sort()) {
    const g = fm(join(gd, gf)).data;
    const re = new RegExp(g.input_match);
    const hits = FAMILY.filter((s) => re.test(JSON.stringify({ skill: `${plugOf(s)}:${s}` })) && re.test(JSON.stringify({ skill: s })));
    const expected = g.max === 0 ? FAMILY.filter((s) => s !== tag) : [tag];
    say(JSON.stringify(hits) === JSON.stringify(expected), `${c}/${gf} matches exactly [${expected.join(",")}] (got [${hits.join(",")}])`);
    say(!re.test(JSON.stringify({ skill: "code-review" })) && !re.test(JSON.stringify({ skill: "verify" })), `${c}/${gf} ignores built-ins`);
  }
}

console.log(failures ? `\n${failures} FAILURE(S)` : "\nall grader checks pass");
process.exit(failures ? 1 : 0);
