---
name: knowledge-retrieval
description: Synthesizes knowledge from your Readwise Reader library by prioritizing highlights and annotations across documents. Use when the user asks for references from their reading, wants to surface saved knowledge, or needs cross-document synthesis.
---

# Knowledge retrieval

Answer from what the user has read, not from what they saved: their highlights and notes are the highest-signal content in the library, because they record what the user judged important. Finding the material is the library-search skill's job; this skill decides what to surface and how to combine it.

<priority>
Surface material in this order, and say which tier each item comes from:

1. Highlighted and annotated (the user marked it and wrote a note)
2. Highlighted
3. Document-level notes
4. Partly read
5. Saved but unread: the topic mattered enough to save, but nothing in it has been confirmed useful

Use `search_highlights` for tiers 1-2 across the library, and `get_highlights(doc_id)` to pull every highlight from a document that matched.
</priority>

<synthesis>
- **Synthesize by point, not by document.** When several documents touch a topic, state each point once and cite every highlight that supports it, quoted, with its document title. A list of five articles is not an answer.
- **Where documents disagree, lay the positions side by side**, each with its supporting highlight, and add where the user stands only when their own notes say so.
- **Tie it to the work in front of the user.** When they ask for references while building or writing something, say for each highlight whether it supports, challenges, or gives background to that specific work.
- **Name the gaps**: subtopics with saved documents but no highlights, and adjacent subtopics with nothing saved.
- **Keep the user's words distinct from yours.** Highlights and notes are quoted verbatim and attributed; your synthesis is marked as yours, so the user can tell what they wrote from what was inferred.
</synthesis>

Depth follows the ask: a quick reference wants the few most relevant highlights with their sources; a research brief searches documents, pulls their highlights, and cross-references them; a comprehensive review adds tag-based discovery and organizes by subtopic or chronology.
