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

```
Reading Digest ([time range])

Activity:
- [N] new items saved
- [N] moved to Later
- [N] archived (completed)
- [N] highlights created

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

### 4. Offer Insights

If notable patterns emerge:
- Large inbox: "Your inbox has [N] items -- consider running /triage"
- Reading velocity: "You've been saving [N] items/week but archiving [M]"
- Category skew: "Most of your recent saves are [category]"

## Examples

```
/digest
/digest --daily
/digest --since 2025-01-01
```
