---
name: knowledge-retrieval
description: Synthesizes knowledge from your Readwise Reader library by prioritizing highlights and annotations across documents. Use when the user asks for references from their reading, wants to surface saved knowledge, or needs cross-document synthesis.
metadata:
  author: Fred Bliss
  version: 1.0.0
  last_verified: "2026-04-02"
---

# Knowledge Retrieval

The intelligence for surfacing useful knowledge from your Readwise Reader library. Goes beyond simple search to synthesize information across multiple saved documents, prioritize your own highlights and annotations, and connect saved knowledge to your current work.

## Highlight Priority Hierarchy

Your own highlights and notes are the highest-signal content in your library. They represent what you found important enough to mark. Retrieval should always prioritize them.

```
1. Highlighted + annotated (you marked it AND wrote a note)
2. Highlighted (you marked it as important)
3. Annotated/noted at document level (you wrote about the document)
4. Partially read (you engaged with it)
5. Saved but unread (you saved it, so the topic mattered)
```

## Cross-Document Synthesis

When multiple documents touch the same topic, synthesize rather than list:

### Pattern: Topic Synthesis

Given a topic query, collect highlights from multiple documents and present a unified brief:

```
From your reading on "[topic]":

Key insights (from [N] documents):
1. [Synthesized point from multiple highlights]
   - "[highlight]" (from [doc1])
   - "[highlight]" (from [doc2])

2. [Another synthesized point]
   - "[highlight]" (from [doc3])

Your notes:
- [Your annotation from doc1]
- [Your annotation from doc2]
```

### Pattern: Perspective Mapping

When documents present different viewpoints on a topic:

```
Perspectives on "[topic]" from your library:

View 1: [Summary]
- From: [document title]
- Key point: "[highlight]"

View 2: [Summary]
- From: [document title]
- Key point: "[highlight]"

Your position (based on your notes):
- [Synthesized from your annotations]
```

## Integration with Current Work

When the user is working on something and asks for references:

### 1. Understand the Work Context
- What is the user currently building/writing/researching?
- What specific aspect needs supporting evidence?
- What format would be most useful? (quotes, summaries, links)

### 2. Match Library Content
- Search for topic keywords from the current work
- Look for highlights that directly support or challenge the work
- Find documents that provide background or context

### 3. Present as Actionable Knowledge
Instead of:
```
Here are 5 articles about X.
```

Present as:
```
From your reading on [topic]:

For your [current task], these highlights are most relevant:
1. "[highlight]" -- supports [aspect of their work]
   Source: [title] by [author]

2. "[highlight]" -- provides context on [related aspect]
   Source: [title]

Background reading (saved but not yet highlighted):
- [Title] -- likely relevant based on summary
```

## Retrieval Strategies

### Deep Retrieval (for focused research)
1. Search documents by topic
2. For each matching document, fetch highlights
3. Cross-reference highlights across documents
4. Synthesize into a knowledge brief

### Quick Retrieval (for casual reference)
1. Search highlights directly (fastest path to your marked content)
2. Include document context for each highlight
3. Present top 5-10 most relevant

### Exhaustive Retrieval (for comprehensive review)
1. Search all documents and highlights
2. Include tag-based discovery
3. Present organized by subtopic or chronology
4. Note gaps: "You have X articles on [subtopic] but none on [related subtopic]"
