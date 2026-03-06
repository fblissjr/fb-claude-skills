---
description: Save a URL to your Readwise Reader library
argument-hint: "<url> [--tags tag1,tag2] [--notes 'note text'] [--location new|later]"
---

# Save Command

Save a URL to your Readwise Reader library with optional tags, notes, and location.

## Instructions

### 1. Parse the Input

Extract from the user's command:
- **URL** (required): The web page, article, PDF, or video to save
- **Tags**: Comma-separated list of tags to apply
- **Notes**: A note to attach to the saved item
- **Location**: Where to save: `new` (inbox, default), `later`, `archive`

### 2. Save the Document

Call the `save_document` tool with the extracted parameters:
- `url`: The URL to save
- `title`: If the user provided a custom title
- `tags`: Array of tag strings
- `location`: Target location (defaults to `new`)
- `notes`: Optional note text

### 3. Confirm the Save

Present the result:
```
Saved to Reader: [title or URL]
ID: [doc_id]
Location: [inbox/later/archive]
Tags: [tags if any]
```

### 4. Handle Duplicates

If the document already exists (HTTP 200 instead of 201), note this:
```
This URL is already in your Reader library.
ID: [doc_id]
```

## Examples

```
/save https://example.com/article
/save https://example.com/article --tags research,ai --notes "Follow up on this"
/save https://example.com/paper.pdf --location later --tags papers
```
