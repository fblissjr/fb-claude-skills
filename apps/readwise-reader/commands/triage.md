---
description: Triage your Readwise Reader inbox
argument-hint: "[--location new|later] [--limit N] [--category article|pdf|...]"
---

# Triage Command

Process your Reader inbox by reviewing items and deciding what to keep, save for later, archive, or delete.

## Instructions

### 1. Load Inbox Items

Call `get_inbox` to fetch unprocessed items:
- Default: items in `new` (inbox) location
- Apply category filter if specified
- Default limit: 10 items per batch

### 2. Present Items for Review

Show a numbered list of inbox items:
```
Your Reader inbox ([N] items):

1. **[Title]** ([category], [word_count] words)
   [Summary if available, first 100 chars]
   Saved: [date] | Source: [site_name]

2. **[Title]** ([category])
   ...

Actions: 'later' (save for reading), 'archive' (done), 'delete' (remove)
```

### 3. Process Triage Decisions

When the user provides decisions, use `triage_document` or `batch_triage`:

- **"later"** or **"keep"**: Move to `later` location
- **"archive"** or **"done"**: Move to `archive`
- **"delete"** or **"remove"**: Delete from Reader
- **Tags**: Apply tags during triage if specified

Accept decisions in these formats:
- `1: later, 2: archive, 3: delete`
- `keep 1,2,4 -- archive 3,5`
- Natural language: "Archive items 1 and 3, save 2 for later, delete the rest"

### 4. Confirm Actions

After processing:
```
Triage complete:
- 3 moved to Later
- 2 archived
- 1 deleted
[N] items remaining in inbox
```

### 5. Offer Next Batch

If more items remain:
```
[N] more items in your inbox. Continue triaging?
```

## Examples

```
/triage
/triage --limit 5
/triage --category article
```
