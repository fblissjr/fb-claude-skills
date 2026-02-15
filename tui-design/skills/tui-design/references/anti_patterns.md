last updated: 2026-02-15

# TUI Anti-Patterns

Each anti-pattern includes a name, real-world code example, why it breaks, and the fix.

## 1. Rainbow Color Syndrome

Every column gets a different color with no semantic meaning.

**Bad:**
```python
table.add_column("Name", style="cyan", no_wrap=True)
table.add_column("Sessions", justify="right", style="green")
table.add_column("Last Active", style="yellow", no_wrap=True)
table.add_column("Models", style="magenta")
table.add_column("Branches", style="blue")
```

**Why it breaks:** Five colors, zero meaning. The user cannot tell at a glance what matters. Cyan for names? Why? Magenta for models? The colors are decorative noise that makes the table harder to scan, not easier.

**Fix:**
```python
table.add_column("Name", no_wrap=True)             # default (primary data)
table.add_column("Sessions", justify="right")       # default
table.add_column("Last Active", style="dim")        # dim = secondary info
table.add_column("Models")                          # default
table.add_column("Branches")                        # default
# Color only on values that need it: status=green/red, stale dates=yellow
```

## 2. Manual Layout Instead of Rich Components

Building table-like output with hardcoded widths, `ljust()`/`rjust()`, format specs, and string concatenation instead of using Rich's layout engine. These two patterns look different but share a root cause: reimplementing what Rich already does, poorly.

**Bad (hardcoded width arithmetic):**
```python
max_project_width = 20
project_prefix = f"[{project_name}]".ljust(max_project_width + 2) + " "
return f"{project_prefix}{date_str}  {size_kb:5.0f} KB  {summary}{suffix}"
```

`20` is arbitrary. On a 200-column terminal, it wastes 180 columns. On an 80-column terminal with a long project name, it overflows. The `+ 2` accounts for brackets but this coupling is invisible. When anyone changes the format, they must hunt for every magic number.

**Bad (string concatenation):**
```python
parts = []
if show_project:
    proj = meta.project_name
    if len(proj) > 16:
        proj = proj[:14] + ".."
    parts.append(f"[{proj}]")

parts.append(f"{date_str:>14s}")
parts.append(f"{size_str:>8s}")
parts.append(summary_text)
return "  ".join(parts)
```

Manual truncation (`[:14] + ".."`) is inconsistent -- should be `...` or use Rich's `overflow`. Right-alignment with format specs (`>14s`) breaks when data exceeds the width. The spacing (`"  ".join`) is fixed regardless of terminal width. Every function that formats output reinvents this logic differently.

**Why both break the same way:** They produce output that looks correct at exactly one terminal width and breaks at every other width. They force the developer to manually handle truncation, alignment, and spacing -- three things Rich's Table does automatically. And they scatter width assumptions across multiple functions, making changes fragile.

**Fix (one Rich Table replaces both patterns):**
```python
from rich.table import Table

table = Table(expand=True, show_header=False, box=None, padding=(0, 1))
table.add_column("Project", ratio=2, min_width=10, no_wrap=True)
table.add_column("Date", ratio=2, min_width=10, style="dim", no_wrap=True)
table.add_column("Size", ratio=1, justify="right", style="dim")
table.add_column("Summary", ratio=4, overflow="ellipsis")
# Rich handles truncation, alignment, spacing, and terminal width automatically
```

## 3. Inconsistent Truncation

The same data type is truncated differently across functions.

**Bad:**
```python
# In function A:
if len(proj) > 16:
    proj = proj[:14] + ".."

# In function B:
if len(project_name) > max_project_width:
    project_name = project_name[:max_project_width - 2] + ".."

# In function C:
proj_display = project_name[:20]  # just chop it
```

**Why it breaks:** Three functions, three truncation strategies. The user sees the same project name displayed three different ways. The ellipsis is sometimes `..` and sometimes not present at all. The truncation point varies (14, 18, 20).

**Fix:** Use Rich columns with `overflow="ellipsis"` everywhere. The table handles truncation consistently. If you must truncate manually, create one utility:

```python
from rich.text import Text

# Let Rich handle it via column overflow:
table.add_column("Project", overflow="ellipsis", no_wrap=True, min_width=10)

# Or if you must do it manually, one function:
def truncate(text: str, max_len: int) -> str:
    """Consistent truncation with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "\u2026"  # unicode ellipsis character
```

## 4. Static Strings for Interactive Widgets

Building fixed-width strings for Questionary choices that display in variable-width terminals.

**Bad:**
```python
terminal_width = get_terminal_width()
used = sum(len(p) for p in parts) + len(parts) * 2 + 6  # spacing + checkbox
available = max(20, terminal_width - used)
summary = summary_text[:available]

display = f"{proj_prefix} [{session_count} sessions] {slug}"
choices.append(questionary.Choice(title=display, value=paths))
```

**Why it breaks:** The width calculation is fragile. `+ 6` accounts for checkbox width, but this is an implementation detail of Questionary that could change. `sum(len(p) for p in parts)` counts characters, not display width (Unicode and ANSI escapes break this). The summary truncation is recalculated every time instead of letting the terminal handle reflow.

**Fix:**
```python
# Keep choices simple -- let the terminal handle wrapping
label = f"{project_name} - {session_count} sessions - {date_range}"
choices.append(questionary.Choice(title=label, value=paths))

# For complex choices, use a Rich-formatted table as the display:
from rich.console import Console
from rich.table import Table

console = Console()

def format_choice(project: str, sessions: int, date: str) -> str:
    """Format a single choice line. Keep it simple."""
    return f"{project}  ({sessions} sessions, {date})"
```

## 5. Mixed Abstraction Levels

Using Rich Tables for some output and manual print formatting for other output in the same CLI.

**Bad:**
```python
# Summary uses Rich Table
table = Table(title="Projects")
table.add_column("Name")
# ...
console.print(table)

# But detail view uses manual formatting
print(f"  Project: {name}")
print(f"  Sessions: {count}")
print(f"  Last Active: {date}")
print(f"  Models: {', '.join(models)}")
```

**Why it breaks:** The summary respects terminal width and color settings. The detail view does not. If the user pipes output, the Rich Table degrades cleanly but the `print()` statements still work. But the styling is inconsistent -- the user sees two different design languages in the same tool.

**Fix:**
```python
# Detail view also uses Rich
from rich.table import Table

detail = Table(show_header=False, box=None, expand=False, padding=(0, 2))
detail.add_column("Key", style="bold", no_wrap=True)
detail.add_column("Value")
detail.add_row("Project", name)
detail.add_row("Sessions", str(count))
detail.add_row("Last Active", date)
detail.add_row("Models", ", ".join(models))
console.print(detail)
```

## 6. No Minimum Width Handling

Claiming to support narrow terminals but not actually testing it.

**Bad:**
```python
# "Responsive" layout that only works at 120+
table.add_column("Name", width=22)
table.add_column("Status", width=12)
table.add_column("Date", width=14)
table.add_column("Model", width=12)
table.add_column("Duration", width=8)
table.add_column("Messages", width=6)
table.add_column("Summary", width=40)
# Total: 114 columns minimum + padding = ~130 columns
```

**Why it breaks:** At 80 columns, Rich either wraps messily or truncates critical data. Fixed widths cannot adapt. The "Summary" column, likely the most useful, gets squeezed to nothing.

**Fix:**
```python
table = Table(expand=True)
table.add_column("Name", ratio=3, min_width=10, no_wrap=True)
table.add_column("Status", ratio=1, min_width=6)
table.add_column("Date", ratio=2, min_width=10, style="dim")
# Only show extra columns at wider terminals
if console.width >= 120:
    table.add_column("Model", ratio=2, style="dim")
    table.add_column("Duration", ratio=1, justify="right", style="dim")
table.add_column("Summary", ratio=4, overflow="ellipsis")
```

## 7. Wasted Vertical Space

Blank lines, sparse formatting, decorative spacing that pushes useful content off screen.

**Bad:**
```python
console.print()
console.print(Panel("Projects", style="bold"))
console.print()
console.print(table)
console.print()
console.print(f"  Total: {count} projects")
console.print()
```

**Why it breaks:** Four blank lines in 7 lines of output. On a 24-row terminal, this wastes 17% of the viewport on nothing. The Panel around a single word is pure decoration -- bold text does the same job.

**Fix:**
```python
console.print("[bold]Projects[/bold]")
console.print(table)
console.print(f"Total: {count} projects", style="dim")
```

## 8. Information-Free Chrome

Borders, boxes, and decorations that communicate nothing.

**Bad:**
```python
panel = Panel(
    Group(table, rule, stats_text),
    title="Session Browser",
    subtitle="Use arrow keys to navigate",
    border_style="bright_blue",
    box=box.DOUBLE_EDGE,
)
```

**Why it breaks:** The double-edge border costs 2 columns on each side and 2 rows (top/bottom). The title repeats what the user already knows (they launched the session browser). The subtitle describes standard terminal behavior. The blue border is decorative. Net information added: zero. Screen space consumed: significant.

**Fix:**
```python
# Title only if needed for disambiguation (multiple panels on screen)
# No border unless separating distinct sections
console.print("[bold]Session Browser[/bold]")
console.print(table)
console.print(stats_text, style="dim")
```

## 9. Wrong Component for the Data

Using a complex component when a simpler one communicates better.

**Bad:**
```python
# Displaying 3 key-value pairs in a full table
table = Table(title="Configuration")
table.add_column("Setting", style="cyan")
table.add_column("Value", style="green")
table.add_row("Model", "claude-sonnet-4-5-20250929")
table.add_row("Max Tokens", "4096")
table.add_row("Temperature", "0.7")
```

**Why it breaks:** A 3-row table with header, borders, and column separators uses 7+ lines for 3 values. The component is heavier than the data.

**Fix:**
```python
# Simple key-value with alignment
console.print("[bold]Model:[/bold] claude-sonnet-4-5-20250929")
console.print("[bold]Max Tokens:[/bold] 4096")
console.print("[bold]Temperature:[/bold] 0.7")

# Or if you have many pairs, a headerless table:
kv = Table(show_header=False, box=None, padding=(0, 2))
kv.add_column("Key", style="bold", no_wrap=True)
kv.add_column("Value")
for k, v in config.items():
    kv.add_row(k, str(v))
console.print(kv)
```
