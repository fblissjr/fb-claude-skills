---
name: library-search
description: Decomposes natural language queries into targeted searches across Readwise Reader documents, highlights, and tags. Use when the user searches their reading library, asks what they saved about a topic, or wants to find specific highlights.
metadata:
  author: Fred Bliss
  version: 1.0.0
  last_verified: "2026-04-02"
---

# Library Search

The search intelligence behind Readwise Reader queries. Transforms a natural language question into targeted searches across your reading library and produces ranked, relevant results.

## The Goal

Turn this:
```
"What articles have I saved about distributed systems that I highlighted?"
```

Into targeted searches:
```
Documents: search_library("distributed systems", limit=30)
Highlights: search_highlights("distributed systems", limit=20)
Tags: get_documents_by_tag("distributed-systems")
```

Then synthesize into a prioritized knowledge brief.

## Query Decomposition

### Step 1: Identify Query Type

| Query Type | Example | Strategy |
|-----------|---------|----------|
| **Topic search** | "articles about X" | Broad document search + highlight search |
| **Recall** | "that article I saved about X" | Search titles and summaries, prioritize recent saves |
| **Highlight retrieval** | "my notes on X" | Prioritize highlight search, include annotations |
| **Tag browse** | "everything tagged X" | Tag-based document lookup |
| **Status query** | "what's in my inbox" | Location-filtered document list |
| **Cross-reference** | "X related to Y" | Multiple searches, intersect results |

### Step 2: Extract Search Components

From the query, extract:
- **Keywords**: Core topic terms
- **Category hints**: "articles", "PDFs", "tweets" map to category filters
- **Location hints**: "inbox", "saved for later", "archived" map to location filters
- **Tag hints**: Explicit tag references
- **Time constraints**: "this week", "last month", "recent"
- **Engagement signals**: "highlighted", "annotated", "read" suggest filtering by reading_progress or highlight count

### Step 3: Generate Search Plan

For each query type, determine which tools to call and in what order:

**Topic search:**
1. `search_library(query, category?, limit=30)` -- broad document search
2. `search_highlights(query, limit=20)` -- parallel highlight search
3. Merge and rank by: documents with highlights > documents with notes > title matches

**Recall search:**
1. `search_library(query, limit=20)` -- focus on titles
2. If few results, broaden: remove filters, try alternate terms

**Tag browse:**
1. `list_tags()` -- find matching tag keys
2. `get_documents_by_tag(tag)` -- fetch tagged documents

## Result Ranking

### Scoring Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Highlight count | 0.3 | Documents you highlighted are more valuable |
| Recency | 0.25 | More recently saved/updated items rank higher |
| Title/summary match | 0.25 | Direct keyword match in title or summary |
| Reading progress | 0.1 | Partially read items may be more relevant than unread |
| Tag match | 0.1 | Exact tag match boosts relevance |

### Priority Hierarchy

For knowledge retrieval:
```
Highlighted + annotated documents > Highlighted documents > Read documents > Saved but unread
```

## Fallback Strategies

When initial search returns too few results:
1. Remove category/location filters
2. Try alternate keyword formulations
3. Search highlights if only documents were searched (and vice versa)
4. Suggest the user sync their library if data seems stale
