---
name: tui-design
description: Design functional, readable terminal UIs with proper visual hierarchy, semantic color, and responsive layout. Use when building CLI tools, interactive prompts, dashboards, or any terminal output with Rich, Textual, Questionary, or Click. Triggers on "terminal UI", "TUI", "Rich table", "CLI output", "terminal dashboard", "questionary prompt", "make this look better in the terminal".
metadata:
  author: Fred Bliss
  version: 0.1.0
---

# Terminal UI Design

Design functional, readable, responsive terminal interfaces. Terminal UIs have hard constraints that require different design thinking than web: monospace fonts, limited color palette, fixed viewport width, no CSS layout engine. This skill ensures Claude generates TUI code that works at any terminal width, communicates hierarchy through typography weight rather than decoration, and uses color semantically.

## Design Thinking

Before writing any TUI code, answer five questions:

1. **Data shape.** List, table, tree, key-value pairs, progress indicator, or selection menu? The shape determines which Rich component to use. Do not choose a component and then force data into it.

2. **Information hierarchy.** What is the primary data the user needs? What is secondary context? What is metadata they rarely need? Primary data gets normal weight. Secondary gets dim. Metadata gets hidden behind a `--verbose` flag or revealed on selection.

3. **Terminal constraints.** What is the minimum width you must support? (80 columns is the safe default.) Does the output need to work when piped to a file or another program? Does the user's terminal support color? Always detect these -- never assume.

4. **Interaction model.** Is this read-only output (Rich), interactive selection (Questionary), or live-updating (Rich Live/Textual)? Each model has different component rules. Do not mix Rich print statements with Questionary prompts without clear visual separation.

5. **Density target.** Dashboards need high information density (multiple panels, compact tables). Wizards need low density (one question at a time, generous whitespace). Match the density to the task, not the amount of data.

## Five Principles

### 1. Semantic Color

Color means something or it means nothing. Every color in your palette must map to a meaning.

**Rules:**
- Maximum 4 colors per view. One primary, one accent, one success/error, one dim.
- Color encodes meaning: green = success/active, red = error/danger, yellow = warning/pending, dim = secondary info.
- Never use color as the only differentiator. Combine with position, weight, or icons.
- Test with `NO_COLOR=1` -- the output must still be readable without any color.

**Palette (16-color safe):**
| Semantic Role | Color | Rich Style | Usage |
|--------------|-------|-----------|-------|
| Primary data | white/default | `""` | Main content, values, names |
| Secondary info | dim | `dim` | Timestamps, IDs, metadata |
| Success/active | green | `green` | Status OK, active items, counts |
| Error/danger | red | `red` | Errors, failures, critical |
| Warning/pending | yellow | `yellow` | Warnings, pending, stale |
| Accent/header | bold | `bold` | Headers, titles, emphasis |

**Wrong:** Different color for every column in a table (rainbow syndrome).
**Right:** All data in default color, status column colored by value, headers bold.

### 2. Responsive Layout

Terminal width varies from 80 to 300+ columns. Your layout must handle all of them.

**Rules:**
- Zero hardcoded widths. Use Rich's `ratio` parameter for proportional columns.
- Set `min_width` on critical columns, let others flex.
- Use `overflow="ellipsis"` or `overflow="fold"` -- never manually truncate with `[:N]`.
- Test at 80, 120, and 200 columns: `COLUMNS=80 python your_script.py`.
- When piped (`not console.is_terminal`), output plain text with no styling.

**Column sizing pattern:**
```python
from rich.table import Table

table = Table(expand=True)  # fills terminal width
table.add_column("Name", ratio=3, min_width=12, no_wrap=True)
table.add_column("Status", ratio=1, min_width=6)
table.add_column("Details", ratio=4)  # gets remaining space
```

**Wrong:** `table.add_column("Name", width=22)` -- breaks at narrow terminals, wastes space at wide ones.
**Right:** `table.add_column("Name", ratio=3, min_width=12)` -- proportional with a floor.

### 3. Right Component for the Data

Rich has many components. Choosing the wrong one forces you into manual formatting to compensate.

**Decision tree:**
| Data Shape | Component | When to Use |
|-----------|-----------|------------|
| Rows x Columns | `Table` | Comparing items across attributes |
| Key: Value pairs | `Table` (2-col, no header) or `Panel` | Config display, detail views |
| Hierarchical | `Tree` | File systems, dependency trees, nested categories |
| Sequential items | `Table` (1 data col + index) | Ordered lists, search results |
| Long text | `Panel` or `Markdown` | Help text, descriptions, error details |
| Multiple sections | `Columns` or `Layout` | Dashboards, side-by-side comparison |
| Progress | `Progress` | Long operations with known/estimated completion |

**Wrong:** Using `print()` with `f"{'name':<20} {'value':>10}"` when Rich Table exists.
**Wrong:** Using a full Table for a single key-value pair.
**Right:** Match the component to the data shape, then configure it.

### 4. Visual Hierarchy Through Typography

Terminal typography is limited to: **bold**, dim, underline, and normal. Use these consistently.

**Rules:**
- Bold = headers, titles, section labels. Nothing else.
- Normal weight = primary data. This is the default -- do not add styles to it.
- Dim = secondary info (timestamps, IDs, counts, paths).
- Underline = sparingly, for column headers if not using a Table.
- One border style per view. Do not mix `box.ROUNDED`, `box.HEAVY`, and `box.SIMPLE`.

**Wrong:** Bold values, colored headers, underlined labels, italic descriptions -- all in one view.
**Right:** Bold headers, normal data, dim metadata. One border style throughout.

### 5. Progressive Density

Show the minimum useful information by default. Let the user request more.

**Rules:**
- Default output fits in 20 lines or fewer.
- `--verbose` / `-v` adds secondary columns, timestamps, IDs.
- `--json` outputs machine-readable format (no styling, no tables).
- Interactive detail: show summary table, let user select a row for full detail.
- Empty state: always handle zero results with a clear message, not an empty table.

**Wrong:** Showing 15 columns by default because the data has 15 fields.
**Right:** Showing 4 columns by default, adding the rest with `-v`.

## Process

When implementing a terminal UI:

1. **Pick the component** from the decision tree in Principle 3. If the data doesn't fit any component cleanly, reconsider the data shape.

2. **Define hierarchy.** Label every field as primary, secondary, or metadata. Primary fields show by default. Secondary shows with `-v`. Metadata shows on selection or `--debug`.

3. **Assign max 4 semantic colors.** Map each to a meaning using the palette from Principle 1. If you need a 5th color, you have too many concerns in one view -- split it.

4. **Build with Rich's layout engine.** Use `ratio` and `min_width` for columns. Use `Table(expand=True)`. Never use `ljust()`, `rjust()`, `f"{val:>14s}"`, or manual padding.

5. **Test at 80, 120, 200 columns.** Run with `COLUMNS=80`, `COLUMNS=120`, `COLUMNS=200`. All three must be readable.

6. **Test piped output.** Run with `| cat` or `| head`. Verify no ANSI escape codes leak and data is still parseable.

7. **Test edge cases.** Empty data, one row, 1000 rows, very long strings, Unicode. Every case must produce readable output.

## Anti-Patterns

See [references/anti_patterns.md](references/anti_patterns.md) for detailed examples with before/after code.

Summary of what to avoid:
- Rainbow color syndrome (5+ colors with no semantic meaning)
- Manual layout instead of Rich components (`ljust()`, `f"{val:>14s}"`, string concatenation)
- Inconsistent truncation across functions
- Static fixed-width strings for Questionary choices
- Mixing Rich Tables with manual print formatting in the same CLI
- No minimum width handling
- Wasted vertical space (decorative blank lines, sparse tables)
- Information-free chrome (borders that communicate nothing)
- Wrong component for the data shape

## References

- [references/rich_patterns.md](references/rich_patterns.md) -- Rich component selection guide with code examples
- [references/questionary_patterns.md](references/questionary_patterns.md) -- interactive prompt patterns
- [references/anti_patterns.md](references/anti_patterns.md) -- before/after case studies
- [references/layout_recipes.md](references/layout_recipes.md) -- 4 complete recipes (data browser, dashboard, progress, wizard)
