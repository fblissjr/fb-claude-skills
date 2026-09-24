---
name: library-search
description: Decomposes natural language queries into targeted searches across Readwise Reader documents, highlights, and tags. Use when the user searches their reading library, asks what they saved about a topic, or wants to find specific highlights.
---

# Library search

Turn a question about the user's Reader library into calls against this plugin's MCP tools, then merge the results into one ranked answer. The tools read a local DuckDB copy of the library, so results are only as fresh as the last sync.

<tools>
| Need | Call |
|---|---|
| Documents by topic | `search_library(query, category?, location?, tag?, limit=20)` |
| The user's highlights and annotations | `search_highlights(query, tag?, limit=20)` |
| Everything under a tag | `list_tags()` to find the exact key, then `get_documents_by_tag(tag)` |
| Inbox, later, archive listings | `search_library` or `list_documents` with `location` |
| Freshness | `library_stats()` reports `last_sync`; `sync_library()` pulls changes |

Map words in the question onto filters: "articles", "PDFs", "tweets" to `category` (article, email, rss, pdf, epub, tweet, video, note); "inbox", "saved for later", "archived" to `location` (new, later, archive, feed); a named tag to `tag`. Run document and highlight searches in parallel for any topic question, because the user's own highlights are often the answer and a document search alone misses them.
</tools>

<ranking>
Order merged results by engagement: documents with the user's highlights and notes first, then highlighted, then read or partly read, then saved but unread. Within a tier, a direct title or summary match beats a tag-only match. "That article I saved about X" is a recall question: favour title matches and recent saves.
</ranking>

<gotchas>
- **Filtered search is a literal substring match.** With any of `category`, `location` or `tag` set, `search_library` matches the whole query string against title, summary and notes, and only among the most recent 200 filtered documents. A multi-word query matches only where that exact phrase appears. Filter with one or two keywords, or search unfiltered and filter the results yourself.
- **Filtered results come back by recency, not relevance** (an unfiltered search is ranked by BM25). Apply the ranking above either way.
- **Few or no results**: drop filters, try alternate terms, search highlights if only documents were searched and the reverse. If `last_sync` is old or absent, say so and offer `sync_library` before concluding the library has nothing.
</gotchas>

Cross-document synthesis of what the results say belongs to the knowledge-retrieval skill.
