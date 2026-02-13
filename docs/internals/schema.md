last updated: 2026-02-13

# data schemas

Formal schemas for the data files used by skill-maintainer.

## state.json

Location: `skill-maintainer/state/state.json`

Tracks monitoring state across runs. Written by docs_monitor.py, source_monitor.py, and apply_updates.py. Read by all scripts.

```
{
  "docs": {
    "<source_name>": {
      "_watermark": {                          // CDC detect layer state
        "last_modified": "<HTTP Last-Modified header value>",
        "etag": "<HTTP ETag header value>",
        "last_checked": "<ISO 8601 UTC timestamp>"
      },
      "_pages": {                              // CDC identify layer state
        "<page_url>": {
          "hash": "<SHA-256 hex digest of page content>",
          "content_preview": "<first 3000 chars of page content>",
          "last_checked": "<ISO 8601 UTC timestamp>",
          "last_changed": "<ISO 8601 UTC timestamp>"
        }
      },
      "_file_hash": "<SHA-256 hex digest>",    // for local file sources (PDF)
      "_file_last_checked": "<ISO 8601 UTC>"
    }
  },
  "sources": {
    "<source_name>": {
      "last_checked": "<ISO 8601 UTC timestamp>",
      "last_commit": "<12-char git commit hash>",
      "commits_since_last": <integer>
    }
  },
  "updates": {
    "<skill_name>": {
      "last_attempt": "<ISO 8601 UTC timestamp>",
      "changes_count": <integer>,
      "backup_path": "<filesystem path to backup>",
      "status": "pending_review"
    }
  }
}
```

### field details

**docs.\<source\>._watermark** -- Tracks the detect layer for each docs source. `last_modified` and `etag` are compared against HTTP response headers to determine if the bundle has changed since last check. If both are empty, the detect layer always falls through to identify.

**docs.\<source\>._pages.\<url\>** -- Per-page state from the identify layer. `hash` is SHA-256 of the page content extracted from llms-full.txt. `content_preview` stores the first 3000 characters for diff comparison in the classify layer. `last_changed` is only updated when the hash changes.

**docs.\<source\>._file_hash** -- For sources with a `hash_file` config (e.g., PDF guides). Simple SHA-256 of the entire file.

**sources.\<source\>** -- Git-based source tracking. `commits_since_last` counts commits found in the time window. Reset on next check.

**updates.\<skill\>** -- Records of update attempts from apply_updates.py. `status` is always `"pending_review"` (manual review required).

### empty state

An empty or missing state.json is treated as `{}`. All scripts handle this gracefully -- first run captures initial state.

---

## config.yaml

Location: `skill-maintainer/config.yaml`

Defines what to monitor and which skills depend on what.

```yaml
sources:
  <source_name>:
    type: docs | source

    # For type: docs -- CDC pipeline configuration
    llms_full_url: <URL to llms-full.txt>        # optional, enables CDC pipeline
    pages:                                        # optional, filter to these URLs
      - <page_url>
    hash_file: <relative path to local file>     # optional, for PDF/binary monitoring
    check_interval: <duration>                    # informational (24h, 168h, etc.)

    # For type: source -- git-based monitoring
    repo: <git clone URL>
    watched_files:                                # files to track for changes
      - <relative path in repo>
    check_interval: <duration>

skills:
  <skill_name>:
    path: <relative path to skill directory>     # must contain SKILL.md
    sources:                                      # which sources affect this skill
      - <source_name>
    auto_update: false                            # always false (manual review)
```

### source types

**docs** -- Monitors documentation URLs for content changes. Uses the CDC pipeline:
1. HEAD request against `llms_full_url` to check Last-Modified
2. GET llms-full.txt, split into pages, hash each watched page
3. Classify changes as BREAKING/ADDITIVE/COSMETIC

If `llms_full_url` is omitted but `hash_file` is present, only does local file hash comparison.

**source** -- Monitors git repositories. Shallow-clones the repo, checks commits in a time window, analyzes watched files for API changes, scans commit messages for deprecation keywords.

### duration format

`check_interval` uses simple duration strings: `24h` (24 hours), `168h` (1 week), `7d` (7 days). This is informational only -- the actual check frequency is determined by cron/manual invocation, not enforced by the scripts.

### skill-source dependency

Each skill lists the sources it depends on. When a source has changes, `update_report.py` maps those changes to affected skills via this dependency list. A skill may depend on multiple sources (e.g., both docs and a git repo).

---

## change dicts

Internal data structures passed between pipeline stages. Not persisted.

### docs change (from docs_monitor.py)

```python
{
    "source": str,          # source name from config
    "url": str,             # page URL or "file://<path>"
    "classification": str,  # BREAKING | ADDITIVE | COSMETIC | ERROR
    "old_hash": str,        # previous SHA-256 (empty for initial)
    "new_hash": str,        # current SHA-256
    "summary": str,         # "+N -M lines" or "initial capture"
}
```

### source result (from source_monitor.py)

```python
{
    "source": str,
    "repo": str,
    "commits_count": int,
    "changed_files_count": int,
    "watched_hits": list[{
        "file": str,
        "api": list[str],   # first 10 public API names
        "api_count": int,
    }],
    "deprecations": list[str],
    "commits": list[{
        "hash": str,        # 12 chars
        "subject": str,
        "author": str,
        "date": str,        # YYYY-MM-DD
    }],
    "classification": str,  # BREAKING | ADDITIVE | COSMETIC | NONE
}
```

### skill change (from apply_updates.py)

```python
# docs type
{
    "type": "docs",
    "source": str,
    "url": str,
    "hash": str,            # 12 chars
    "last_checked": str,
    "last_changed": str,
}

# source type
{
    "type": "source",
    "source": str,
    "commits": int,
    "last_commit": str,
    "last_checked": str,
}
```
