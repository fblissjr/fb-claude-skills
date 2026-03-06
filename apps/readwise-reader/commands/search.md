---
description: Search your Readwise Reader library
argument-hint: "<query> [--tag tag] [--category article|pdf|...] [--location new|later|archive]"
---

# Search Command

Search across your Readwise Reader library including documents, highlights, and notes.

## Instructions

### 1. Check Sync Status

Before searching, verify the library has been synced:
- Call `library_stats` to check `last_sync`
- If never synced, suggest running `sync_library` first
- If last sync was more than a day ago, mention this in results

### 2. Parse the Query

Extract from the user's command:
- **Query** (required): Search terms
- **Tag filter**: Limit to specific tag
- **Category filter**: article, email, rss, pdf, epub, tweet, video, note
- **Location filter**: new (inbox), later, archive, feed

### 3. Execute Search

Call `search_library` with the extracted parameters. This searches across:
- Document titles
- Document summaries
- Notes
- Full content (when synced)

For highlight-specific searches, also call `search_highlights` in parallel.

### 4. Present Results

Format results by relevance:
```
Found [N] results for "[query]":

1. **[Title]** ([category])
   [Summary snippet or first relevant text]
   Tags: [tags] | Location: [location] | Saved: [date]
   ID: [doc_id]

2. **[Title]** ([category])
   ...
```

If highlights match:
```
Highlights matching "[query]":

1. "[highlight text]" -- [note if any]
   From: [document title]
   Highlighted: [date]
```

### 5. Handle No Results

```
No results found for "[query]" in your Reader library.

Suggestions:
- Try broader search terms
- Check if your library is synced (last sync: [date])
- Run sync_library to pull latest data
```

## Examples

```
/search machine learning
/search "API design" --tag engineering
/search --category pdf --tag research
```
