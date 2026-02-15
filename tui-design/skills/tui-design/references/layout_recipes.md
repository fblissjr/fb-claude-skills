last updated: 2026-02-15

# Layout Recipes

Four complete terminal UI recipes covering the most common patterns.

## Recipe 1: Data Browser

A list-detail pattern: show a summary table, let the user select a row, display full details.

```python
"""Data browser: summary table -> selection -> detail view."""
from rich.console import Console
from rich.table import Table
import questionary

console = Console()


def format_status(status: str) -> str:
    colors = {"active": "green", "stale": "yellow", "error": "red"}
    color = colors.get(status, "")
    return f"[{color}]{status}[/{color}]" if color else status


def build_summary_table(projects: list[dict]) -> Table:
    table = Table(expand=True, title="Projects", title_style="bold")
    table.add_column("#", justify="right", style="dim", ratio=1, min_width=3)
    table.add_column("Name", ratio=3, min_width=10, no_wrap=True)
    table.add_column("Status", ratio=1, min_width=6)
    table.add_column("Sessions", justify="right", ratio=1)

    if console.width >= 100:
        table.add_column("Last Active", ratio=2, style="dim", no_wrap=True)
        table.add_column("Branch", ratio=2, style="dim", overflow="ellipsis")

    for i, p in enumerate(projects, 1):
        row = [str(i), p["name"], format_status(p["status"]), str(p["sessions"])]
        if console.width >= 100:
            row.extend([p["last_active"], p["branch"]])
        table.add_row(*row)

    return table


def build_detail_view(project: dict) -> Table:
    kv = Table(show_header=False, box=None, expand=False, padding=(0, 2))
    kv.add_column("Key", style="bold", no_wrap=True, min_width=12)
    kv.add_column("Value")

    fields = [
        ("Name", project["name"]),
        ("Status", format_status(project["status"])),
        ("Sessions", str(project["sessions"])),
        ("Last Active", project["last_active"]),
        ("Branch", project["branch"]),
        ("Path", project["path"]),
    ]
    for key, val in fields:
        kv.add_row(key, val)

    return kv


def browse_projects(projects: list[dict]) -> None:
    if not projects:
        console.print("[dim]No projects found.[/dim]")
        return

    # Summary
    console.print(build_summary_table(projects))
    console.print()

    # Selection
    choices = [
        questionary.Choice(title=p["name"], value=p)
        for p in projects
    ]
    choices.append(questionary.Choice(title="Exit", value=None))

    selected = questionary.select("Select a project:", choices=choices).ask()
    if selected is None:
        return

    # Detail
    console.print()
    console.print(f"[bold]{selected['name']}[/bold]")
    console.print(build_detail_view(selected))
```

## Recipe 2: Dashboard

Multi-panel display with Rich Layout for monitoring or status views.

```python
"""Dashboard: header + two-column layout with live data."""
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def format_status(status: str) -> str:
    colors = {"active": "green", "stale": "yellow", "error": "red"}
    color = colors.get(status, "")
    return f"[{color}]{status}[/{color}]" if color else status


def build_dashboard(
    projects: list[dict],
    stats: dict,
    recent: list[dict],
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="main", ratio=3),
        Layout(name="sidebar", ratio=1, minimum_size=20),
    )

    # Header
    layout["header"].update(
        Panel("[bold]Project Dashboard[/bold]", box=box.SIMPLE, style="dim")
    )

    # Main: project table
    table = Table(expand=True, box=box.SIMPLE)
    table.add_column("Project", ratio=3, min_width=10, no_wrap=True)
    table.add_column("Status", ratio=1, min_width=6)
    table.add_column("Sessions", ratio=1, justify="right")
    table.add_column("Last Active", ratio=2, style="dim")

    for p in projects:
        table.add_row(
            p["name"],
            format_status(p["status"]),
            str(p["sessions"]),
            p["last_active"],
        )

    layout["main"].update(Panel(table, title="Projects", border_style="dim"))

    # Sidebar: stats
    stats_kv = Table(show_header=False, box=None, padding=(0, 1))
    stats_kv.add_column("Key", style="bold", no_wrap=True)
    stats_kv.add_column("Value", justify="right")
    stats_kv.add_row("Total Projects", str(stats["total"]))
    stats_kv.add_row("Active", f"[green]{stats['active']}[/green]")
    stats_kv.add_row("Stale", f"[yellow]{stats['stale']}[/yellow]")
    stats_kv.add_row("Errors", f"[red]{stats['errors']}[/red]")

    layout["sidebar"].update(Panel(stats_kv, title="Stats", border_style="dim"))

    # Footer: recent activity
    activity = " | ".join(
        f"{r['project']}: {r['action']}" for r in recent[:3]
    )
    layout["footer"].update(
        Panel(f"[dim]Recent: {activity}[/dim]", box=box.SIMPLE)
    )

    return layout


def show_dashboard(projects, stats, recent) -> None:
    dashboard = build_dashboard(projects, stats, recent)
    console.print(dashboard)
```

For live-updating dashboards, wrap with `Live`:

```python
from rich.live import Live
import time

def live_dashboard(poll_fn, interval: float = 2.0) -> None:
    """Live-updating dashboard."""
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            data = poll_fn()
            layout = build_dashboard(data["projects"], data["stats"], data["recent"])
            live.update(layout)
            time.sleep(interval)
```

## Recipe 3: Progress Reporter

Multi-step operation with named tasks and completion status.

```python
"""Progress reporter: multi-step with named tasks."""
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)

console = Console()


def run_pipeline(steps: list[dict]) -> dict:
    """
    Run a pipeline of named steps with progress.

    Each step: {"name": str, "fn": callable, "total": int | None}
    - total=None means indeterminate (spinner only)
    - total=N means known count (progress bar)
    """
    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        for step in steps:
            if step["total"] is not None:
                task_id = progress.add_task(step["name"], total=step["total"])
                for item in step["fn"]():
                    progress.update(task_id, advance=1)
                    results[step["name"]] = item
            else:
                task_id = progress.add_task(step["name"], total=None)
                results[step["name"]] = step["fn"]()
                progress.update(task_id, total=1, completed=1)

    # Summary after completion
    console.print()
    console.print("[bold]Complete[/bold]")
    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column("Step", style="bold")
    summary.add_column("Result")
    for step in steps:
        summary.add_row(step["name"], "[green]done[/green]")
    console.print(summary)

    return results
```

For a simpler single-operation spinner:

```python
def run_with_spinner(message: str, fn: callable):
    """Single operation with spinner."""
    with console.status(message):
        result = fn()
    console.print(f"[green]Done:[/green] {message}")
    return result
```

## Recipe 4: Selection Wizard

Multi-phase interactive flow with Rich context between Questionary prompts.

```python
"""Selection wizard: multi-phase with context display."""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import questionary

console = Console()


def session_wizard(sessions: list[dict]) -> dict | None:
    """
    Three-phase wizard:
    1. Filter by project
    2. Select session from filtered list
    3. Choose action for selected session
    """
    # Phase 1: Filter
    projects = sorted(set(s["project"] for s in sessions))
    if not projects:
        console.print("[dim]No sessions found.[/dim]")
        return None

    console.print("[bold]Step 1: Select Project[/bold]")
    project = questionary.select(
        "Which project?",
        choices=projects + ["All projects"],
    ).ask()
    if project is None:
        return None

    # Filter
    if project == "All projects":
        filtered = sessions
    else:
        filtered = [s for s in sessions if s["project"] == project]

    if not filtered:
        console.print("[dim]No sessions match.[/dim]")
        return None

    # Phase 2: Show filtered sessions, select one
    console.print()
    console.print("[bold]Step 2: Select Session[/bold]")

    table = Table(expand=True, box=box.SIMPLE)
    table.add_column("#", justify="right", style="dim", ratio=1, min_width=3)
    table.add_column("Date", ratio=2, min_width=10, no_wrap=True)
    table.add_column("Duration", ratio=1, justify="right")
    table.add_column("Summary", ratio=5, overflow="ellipsis")

    for i, s in enumerate(filtered, 1):
        table.add_row(str(i), s["date"], s["duration"], s["summary"])

    console.print(table)
    console.print()

    choices = [
        questionary.Choice(
            title=f"{s['date']} - {s['summary'][:60]}",
            value=s,
        )
        for s in filtered
    ]
    session = questionary.select("Select a session:", choices=choices).ask()
    if session is None:
        return None

    # Phase 3: Action
    console.print()
    console.print("[bold]Step 3: Choose Action[/bold]")

    # Show detail before action choice
    detail = Table(show_header=False, box=None, padding=(0, 2))
    detail.add_column("Key", style="bold", no_wrap=True)
    detail.add_column("Value")
    detail.add_row("Project", session["project"])
    detail.add_row("Date", session["date"])
    detail.add_row("Duration", session["duration"])
    detail.add_row("Model", session.get("model", "unknown"))
    detail.add_row("Messages", str(session.get("messages", 0)))
    console.print(detail)
    console.print()

    action = questionary.select(
        "What do you want to do?",
        choices=[
            questionary.Choice(title="View full transcript", value="view"),
            questionary.Choice(title="Export to markdown", value="export"),
            questionary.Choice(title="Delete session", value="delete"),
            questionary.Choice(title="Cancel", value=None),
        ],
    ).ask()

    if action is None:
        return None

    return {"session": session, "action": action}
```

## General Patterns

### Consistent Function Signatures

All display functions should accept a `Console` instance for testability:

```python
def show_results(results: list[dict], console: Console) -> None:
    """Accept console for testability and pipe detection."""
    ...
```

### Separation of Data and Presentation

Build Rich renderables (Table, Tree, Panel) in one function, print them in another:

```python
# Build (testable, composable)
def build_table(data: list[dict], console: Console) -> Table:
    ...

# Display (thin wrapper)
def show_table(data: list[dict], console: Console) -> None:
    table = build_table(data, console)
    console.print(table)
```

### Testing at Multiple Widths

```bash
# Test responsive behavior
COLUMNS=80 python my_cli.py
COLUMNS=120 python my_cli.py
COLUMNS=200 python my_cli.py

# Test piped output
python my_cli.py | cat
python my_cli.py | head -20

# Test no-color
NO_COLOR=1 python my_cli.py
```
