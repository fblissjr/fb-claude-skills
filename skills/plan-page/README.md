last updated: 2026-10-06

# plan-page

Get a plan you can read in a minute and answer in place.

```
/plan-page add send later to the composer
```

Produces one HTML page. The plan is a tree of claims:

| Level | Answers | Shown as |
|---|---|---|
| Title | What is this? | a short name, with your own words under “Why” |
| 1 | What can someone now do or see? | a UI mockup or a state machine |
| 2 | How does that work? | a call stack, a schema or a snippet |
| 3 | Where? | the code |

Closed, the tree is the summary. Open it one level at a time. Each decision has a number, and a button at the bottom (“3 to answer”) goes to the next one you have not opened. Pick options, edit a schema, comment on any claim or line, then press **Respond** and paste the one answer back to Claude.

Needs `node` to pack the page into a single file. No other dependencies.

See `skills/plan-page/examples/scheduled-send.html` for a full plan.

## Where this copy comes from

This is a port of the `html-plan` plugin in
[anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community/tree/main/html-plan),
taken at upstream version 1.0.0 (commit `f60f045`). The author and the MIT
license in `.claude-plugin/plugin.json` are the upstream ones. It is named
`plan-page` here so that it does not clash with the upstream plugin. The
runtime files keep their upstream names (`htmlplan.css`, `htmlplan.js`).

Apart from the name, this README and the manifest, it differs from upstream
only in `skills/plan-page/runtime/htmlplan.css`: a published plan now follows the
viewer's dark theme. Upstream is a read-only
mirror that closes outside pull requests
([#2406](https://github.com/anthropics/claude-plugins-community/pull/2406)), so
the fix lives here until upstream has it. Then this copy can be retired.

This plugin and `html-plan@claude-community` answer the same requests for a
plan. With both installed, disable one, or call the one you want by name.
