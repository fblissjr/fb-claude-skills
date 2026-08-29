---
name: init-maintenance
description: >-
  Set up skill-maintainer in a repo — creates .skill-maintainer/ with config and
  state tracking, and installs the pre-commit hook. Use when the user says "init
  maintenance", "set up maintenance", "initialize skill-maintainer", or "add
  maintenance to this repo".
argument-hint: "[--force-hook]"
---

# Initialize maintenance in this repo

```bash
uv run skill-maintain init $ARGUMENTS
```

Pass `--force-hook` to overwrite an existing `.git/hooks/pre-commit` — the
prior one is preserved as `.local` and still runs first.

After it completes, tell the user what to edit: `.skill-maintainer/config.json`
holds the upstream doc URLs and any tracked source repos, and both are empty
until filled in.

`init` does **not** write a `best_practices.md` into the repo. The plugin's
bundled `references/best_practices.md` is the copy `/maintain` reads. A repo only
needs a local working copy if it intends to edit the rules, in which case copy
the bundled file across deliberately.

`.skill-maintainer/state/` is gitignored — it holds upstream page snapshots and
the changes log, which are per-machine and would conflict if committed.
