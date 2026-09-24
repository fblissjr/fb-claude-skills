---
name: content-triage
description: Manages the read-it-later lifecycle with decision frameworks for inbox triage. Use when the user wants to process their reading inbox, batch-triage saved items, or assess inbox health metrics.
---

# Content triage

Help the user empty their Reader inbox into a queue they will actually read. Items arrive in location `new` (the inbox); triage moves each to `later` (committed to read), `archive` (processed, still searchable), or deletes it.

<tools>
- `get_inbox(category?, limit=20)` lists `new` items from the local copy, most recent first.
- `triage_document(doc_id, action, tags?)` applies one of `later`, `archive`, `delete`, optionally tagging.
- `batch_triage(actions)` applies many at once; each result row carries its own `success` and `error`, so report failures per item.
- Both update the local copy, so the next `get_inbox` no longer lists moved items.
</tools>

<decisions>
The user decides; you recommend. A recommendation weighs relevance to the user's current work, timeliness (news goes stale, reference material does not), and whether they would act on it. Keep what is relevant and actionable, keep timely items of moderate relevance, archive with descriptive tags what might be needed someday ("tag and release": out of the queue, still findable by search), and delete what is irrelevant or stale. Title and summary are usually enough to recommend; group by category so similar items are judged together.
</decisions>

<gotchas>
- **Delete is not reversible from here.** It removes the document from Reader itself. Delete only items the user named for deletion, and prefer archive when they are unsure.
</gotchas>

<inbox_health>
When the user asks how their inbox is doing, report size, oldest item and its age, and this week's saved versus processed. The house thresholds: healthy under 50 items with nothing older than two weeks and processing outpacing saving; over 100 is overwhelmed. `library_stats` gives `inbox_size`; `reading_digest` gives recent activity.
</inbox_health>
