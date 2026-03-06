---
description: Surface saved knowledge relevant to a topic or your current work
argument-hint: "<topic>"
---

# Reference Command

Surface documents, highlights, and notes from your Reader library that are relevant to a topic or your current work context.

## Instructions

### 1. Understand the Context

The user is looking for previously saved knowledge related to a topic. This could be:
- Research for a task they're working on
- Background reading on a subject
- Specific highlights or notes they made
- Previously saved articles they want to revisit

### 2. Search Broadly

Execute multiple searches in parallel to find relevant material:

1. **Document search**: `search_library(query=topic)` for matching documents
2. **Highlight search**: `search_highlights(query=topic)` for matching highlights/annotations
3. **Tag search**: `get_documents_by_tag(tag=topic)` if the topic matches a known tag

### 3. Synthesize Results

Present a knowledge brief, not just a list of links:

```
Knowledge on "[topic]" from your Reader library:

Key Highlights:
- "[highlight text]" -- from [document title]
  Your note: "[note if any]"
- "[highlight text]" -- from [document title]

Saved Documents ([N]):
1. **[Title]** by [author] ([category])
   [Summary]
   Reading progress: [X]% | Highlights: [N]

2. **[Title]** by [author]
   ...

Related Tags: [tag1], [tag2], [tag3]
```

### 4. Prioritize by Usefulness

Order results by:
1. Documents with highlights (you engaged with these)
2. Documents with notes (you annotated these)
3. Documents matching the topic in title/summary
4. Documents matching in tags only

### 5. Suggest Actions

```
Want to:
- See full highlights from a specific document? (provide ID)
- Save something new on this topic?
- Search with different terms?
```

## Examples

```
/reference machine learning transformers
/reference "API design patterns"
/reference kubernetes security
```
