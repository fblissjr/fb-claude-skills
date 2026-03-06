last updated: 2026-02-15

# Rich Component Patterns

Component selection guide with code examples for common terminal UI patterns.

## Console Setup

Always detect terminal capabilities before rendering.

```python
from rich.console import Console

console = Console()

# Check capabilities
if not console.is_terminal:
    # Piped output: no color, no interactive elements
    # Use console.print() still -- Rich strips styling automatically
    pass

# Get terminal dimensions
width = console.width    # current terminal width
height = console.height  # current terminal height

# Force plain output (honor NO_COLOR env var)
import os
if os.environ.get("NO_COLOR"):
    console = Console(no_color=True)
```

## Responsive Table

The most common component. Use `expand=True` and `ratio` for responsive columns.

```python
from rich.table import Table

def build_project_table(projects: list[dict], console: Console) -> Table:
    """Responsive project listing."""
    table = Table(expand=True, title="Projects", title_style="bold")

    # Required columns (always shown)
    table.add_column("Name", ratio=3, min_width=10, no_wrap=True)
    table.add_column("Status", ratio=1, min_width=6)
    table.add_column("Sessions", ratio=1, justify="right")

    # Optional columns (only at wider terminals)
    show_details = console.width >= 100
    if show_details:
        table.add_column("Last Active", ratio=2, style="dim", no_wrap=True)
        table.add_column("Branch", ratio=2, style="dim")

    for p in projects:
        row = [p["name"], format_status(p["status"]), str(p["sessions"])]
        if show_details:
            row.extend([p["last_active"], p["branch"]])
        table.add_row(*row)

    return table


def format_status(status: str) -> str:
    """Semantic color for status values."""
    colors = {
        "active": "[green]active[/green]",
        "stale": "[yellow]stale[/yellow]",
        "error": "[red]error[/red]",
    }
    return colors.get(status, status)
```

## Key-Value Display

For detail views and configuration display.

```python
from rich.table import Table

def build_detail_view(data: dict) -> Table:
    """Key-value pairs without header or borders."""
    kv = Table(show_header=False, box=None, expand=False, padding=(0, 2))
    kv.add_column("Key", style="bold", no_wrap=True, min_width=12)
    kv.add_column("Value")

    for key, value in data.items():
        kv.add_row(key, str(value))

    return kv
```

For very few pairs (3 or fewer), inline is better:

```python
def print_config(console: Console, model: str, tokens: int, temp: float) -> None:
    console.print(f"[bold]Model:[/bold] {model}")
    console.print(f"[bold]Max Tokens:[/bold] {tokens}")
    console.print(f"[bold]Temperature:[/bold] {temp}")
```

## Tree Display

For hierarchical data: file trees, dependency graphs, nested categories.

```python
from rich.tree import Tree

def build_project_tree(project: dict) -> Tree:
    """Project hierarchy: project -> sessions -> tools."""
    tree = Tree(f"[bold]{project['name']}[/bold]")

    for session in project["sessions"]:
        branch = tree.add(f"{session['date']} ({session['duration']})", style="dim")
        for tool in session["tools"]:
            style = "green" if tool["status"] == "success" else "red"
            branch.add(f"[{style}]{tool['name']}[/{style}]")

    return tree
```

## Panel

For boxed content: help text, summaries, error messages.

```python
from rich.panel import Panel

# Simple info panel
panel = Panel(
    "No sessions found. Run [bold]claude[/bold] to create one.",
    title="Empty",
    border_style="dim",
)

# Error panel
error_panel = Panel(
    f"[red]{error_message}[/red]\n\nTry: [bold]{suggestion}[/bold]",
    title="[red]Error[/red]",
    border_style="red",
)
```

Use panels sparingly. A panel around a single line of text is usually overkill -- bold text works.

## Progress

For operations with known or estimated duration.

```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

def run_with_progress(tasks: list[dict]) -> None:
    """Multi-step progress with named tasks."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        for task_def in tasks:
            task_id = progress.add_task(task_def["name"], total=task_def["total"])
            for _ in range(task_def["total"]):
                do_work()
                progress.update(task_id, advance=1)
```

For indeterminate operations (no total), use a spinner only:

```python
with console.status("Loading sessions..."):
    sessions = load_all_sessions()
```

## Columns (Flowing Multi-Column)

For lists that should fill horizontal space like `ls`.

```python
from rich.columns import Columns

def show_tags(tags: list[str]) -> None:
    """Tags flowing across terminal width."""
    console.print(Columns(tags, padding=(0, 2)))
```

## Layout (Dashboard)

For multi-panel dashboards with fixed regions.

```python
from rich.layout import Layout
from rich.panel import Panel

def build_dashboard() -> Layout:
    """Two-column dashboard with header."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
    )
    layout["body"].split_row(
        Layout(name="left", ratio=2),
        Layout(name="right", ratio=1),
    )
    return layout

# Usage:
layout = build_dashboard()
layout["header"].update(Panel("[bold]Dashboard[/bold]", box=box.SIMPLE))
layout["left"].update(project_table)
layout["right"].update(stats_panel)
console.print(layout)
```

## 16-Color Safe Palette

These colors work on all terminals (including 16-color).

| Rich Style | Use For | Example |
|-----------|---------|---------|
| `""` (default) | Primary data, values | Names, descriptions |
| `bold` | Headers, titles, emphasis | Section headers |
| `dim` | Secondary info, metadata | Timestamps, IDs, paths |
| `green` | Success, active, positive | Status OK, running |
| `red` | Error, danger, negative | Failures, critical |
| `yellow` | Warning, pending, attention | Stale data, caution |
| `blue` | Info, links, references | URLs (sparingly) |
| `bold red` | Critical errors | Fatal messages |
| `bold green` | Completion, major success | "Done!" messages |

**Avoid:** `cyan`, `magenta`, `bright_*` variants unless you have a specific semantic reason. More colors does not mean more clarity.

## Pipe-Safe Output

Always handle non-terminal output gracefully.

```python
def display_results(results: list[dict], console: Console) -> None:
    if console.is_terminal:
        # Rich formatted output
        table = build_results_table(results, console)
        console.print(table)
    else:
        # Plain text for piping
        for r in results:
            console.print(f"{r['name']}\t{r['status']}\t{r['date']}")
```

Or let Rich handle it automatically (it strips formatting when not a terminal):

```python
# Rich auto-detects -- but tables still have box-drawing characters
# For truly clean piped output, check explicitly
console = Console()
if not console.is_terminal:
    console = Console(no_color=True)
```

## Empty State

Always handle zero results explicitly.

```python
def show_results(results: list[dict], console: Console) -> None:
    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    table = build_results_table(results, console)
    console.print(table)
```
