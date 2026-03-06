---
name: content-triage
description: Manages the read-it-later lifecycle with decision frameworks for inbox triage. Use when the user wants to process their reading inbox, batch-triage saved items, or assess inbox health metrics.
metadata:
  author: Fred Bliss
  version: 1.0.0
  last_verified: "2026-03-06"
---

# Content Triage

Intelligence for managing the read-it-later lifecycle. Helps users process their inbox efficiently, make good keep/archive/delete decisions, and maintain a sustainable reading queue.

## The Read-It-Later Lifecycle

```
Saved (new) --> Later (queued for reading) --> Archive (completed/processed)
     |                    |
     +--> Delete          +--> Delete
```

Items enter as `new` (inbox). Triage moves them to `later` (committed to read), `archive` (processed/done), or deletes them.

## Triage Decision Framework

### Quick Assessment Criteria

For each inbox item, evaluate:

1. **Relevance**: Does this relate to current projects, interests, or goals?
   - High: Directly relevant to active work
   - Medium: Generally interesting or useful background
   - Low: Tangential or outdated

2. **Timeliness**: Is this time-sensitive?
   - Urgent: News, announcements, deadlines
   - Evergreen: Reference material, tutorials, research
   - Stale: Old news, resolved discussions

3. **Effort**: How much time would this take to consume?
   - Quick read: < 5 minutes (articles, short posts)
   - Medium: 5-20 minutes (longer articles, papers)
   - Deep: > 20 minutes (books, long-form, technical papers)

4. **Action potential**: Will you actually do something with this?
   - High: Will inform a decision, feed into work, or change behavior
   - Low: "Nice to know" but no concrete use

### Decision Matrix

| Relevance | Timeliness | Action | Decision |
|-----------|-----------|--------|----------|
| High | Any | High | Later (priority) |
| High | Any | Low | Later |
| Medium | Urgent | Any | Later |
| Medium | Evergreen | High | Later |
| Medium | Evergreen | Low | Archive or delete |
| Medium | Stale | Any | Archive or delete |
| Low | Any | Any | Delete |

### Batch Triage Workflow

When triaging multiple items:

1. **Group by category**: Articles together, tweets together, PDFs together
2. **Quick scan**: Title + summary is usually enough for a decision
3. **Apply tags**: Tag items during triage to organize for later retrieval
4. **Set reading order**: Higher-priority items get `later`, lower priority get archived with tags

## Inbox Health Metrics

A healthy inbox means:
- **Size**: Under 50 items (over 100 is overwhelmed)
- **Age**: No items older than 2 weeks (they're stale)
- **Ratio**: Saving fewer items than you process (inbox trending down)

When presenting triage results, surface these metrics:
```
Inbox health:
- Size: [N] items ([healthy/growing/overwhelming])
- Oldest item: [date] ([age])
- This week: +[saved] / -[processed]
```

## Triage Patterns

### The "Two-Minute Rule"
If you can decide in under 2 minutes whether to keep it, decide now. Don't defer decisions on obvious keeps or deletes.

### The "Batch by Category" Pattern
Process all articles first, then all tweets, then all PDFs. Context-switching between types is costly.

### The "Tag and Release" Pattern
For items you might need someday: tag them descriptively, then archive. They're findable via search but out of your active queue.
