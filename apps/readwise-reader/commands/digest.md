---
description: Get a summary of your reading activity
argument-hint: "[--daily|--weekly|--since DATE]"
---

# Digest Command

Get a summary of your recent reading activity, library statistics, and reading patterns.

## Instructions

### 1. Determine Time Range

- `--daily`: Last 24 hours
- `--weekly` (default): Last 7 days
- `--since DATE`: Since the specified ISO date

### 2. Gather Data

Call these tools in parallel:
- `reading_digest(since=...)` for activity summary
- `library_stats()` for overall counts

### 3. Present the Digest

`reading_digest` counts documents *updated* in the range, grouped by current
location and category; it does not count highlights or distinguish a new save
from a move. Report what it returns under those names:

```
Reading Digest ([time range])

Activity ([N] documents updated):
- Inbox: [N] | Later: [N] | Archive: [N]

By Category:
- Articles: [N] | PDFs: [N] | Tweets: [N] | ...

Library Overview:
- Total documents: [N]
- Total highlights: [N]
- Inbox size: [N] items pending
- Tags: [N] unique tags

Recent Saves:
1. [Title] ([category]) -- [date]
2. [Title] ([category]) -- [date]
...

Last synced: [date]
```

### 4. Notable patterns

Add a line only for a pattern the data shows, such as a large inbox (suggest
`/triage`) or recent activity skewed to one category.

## Examples

```
/digest
/digest --daily
/digest --since 2025-01-01
```
