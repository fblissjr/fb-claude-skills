last updated: 2026-02-15

# Questionary Patterns

Interactive prompt patterns for terminal selection, input, and multi-step workflows.

## Choice Formatting

Keep choices readable at any terminal width. Do not manually calculate available space.

### Simple Choices

```python
import questionary

# Good: concise, scannable
choice = questionary.select(
    "Select a project:",
    choices=[
        questionary.Choice(title="my-app (12 sessions)", value="my-app"),
        questionary.Choice(title="api-server (3 sessions)", value="api-server"),
        questionary.Choice(title="docs-site (1 session)", value="docs-site"),
    ],
).ask()
```

**Bad:** Cramming multiple data points into a padded fixed-width string.
```python
# Don't do this
title = f"{'my-app':<20} {'12 sessions':>14} {'2026-02-10':>12} {'main':>10}"
```

### Rich-Enhanced Choices

Questionary choices are plain text. To show rich context before the prompt, use Rich for the display and Questionary for the selection.

```python
from rich.console import Console
from rich.table import Table
import questionary

console = Console()

def select_project(projects: list[dict]) -> str | None:
    """Show a Rich table, then prompt for selection."""
    # Display context with Rich
    table = Table(expand=True, title="Projects", title_style="bold")
    table.add_column("#", justify="right", style="dim", ratio=1, min_width=3)
    table.add_column("Name", ratio=3, min_width=10)
    table.add_column("Sessions", justify="right", ratio=1)
    table.add_column("Last Active", style="dim", ratio=2)

    for i, p in enumerate(projects, 1):
        table.add_row(str(i), p["name"], str(p["sessions"]), p["last_active"])

    console.print(table)
    console.print()

    # Simple choice list for selection
    choices = [
        questionary.Choice(title=p["name"], value=p["id"])
        for p in projects
    ]
    return questionary.select("Select a project:", choices=choices).ask()
```

### Grouped Choices

For long lists, group by category with separators.

```python
import questionary

def select_model(models: list[dict]) -> str | None:
    """Grouped model selection."""
    choices = []
    current_provider = None

    for m in models:
        if m["provider"] != current_provider:
            if current_provider is not None:
                choices.append(questionary.Separator())
            choices.append(questionary.Separator(f"--- {m['provider']} ---"))
            current_provider = m["provider"]

        choices.append(questionary.Choice(
            title=f"{m['name']} ({m['params']})",
            value=m["id"],
        ))

    return questionary.select("Select a model:", choices=choices).ask()
```

## Checkbox Patterns

For multi-select with sensible defaults.

```python
import questionary

def select_columns(available: list[str], defaults: list[str]) -> list[str]:
    """Multi-select with pre-checked defaults."""
    choices = [
        questionary.Choice(title=col, checked=col in defaults)
        for col in available
    ]
    return questionary.checkbox(
        "Select columns to display:",
        choices=choices,
    ).ask()
```

## Text Input with Validation

```python
import questionary

def get_project_name() -> str:
    """Validated text input."""
    return questionary.text(
        "Project name:",
        validate=lambda text: (
            True if text and len(text) <= 50 and text.replace("-", "").replace("_", "").isalnum()
            else "Must be 1-50 alphanumeric characters (hyphens and underscores allowed)"
        ),
    ).ask()
```

## Confirmation

```python
import questionary

def confirm_action(message: str, default: bool = False) -> bool:
    """Yes/no with explicit default."""
    return questionary.confirm(message, default=default).ask()
```

## Multi-Phase Wizard

A wizard collects input across multiple steps with Rich output between phases.

```python
from rich.console import Console
from rich.panel import Panel
import questionary

console = Console()

def setup_wizard() -> dict:
    """Multi-phase setup wizard."""
    config = {}

    # Phase 1: Project type
    console.print("[bold]Step 1 of 3: Project Type[/bold]")
    config["type"] = questionary.select(
        "What kind of project?",
        choices=["CLI tool", "Library", "Web service", "Script"],
    ).ask()
    if config["type"] is None:
        return {}  # user cancelled

    # Phase 2: Configuration (based on Phase 1 answer)
    console.print()
    console.print("[bold]Step 2 of 3: Configuration[/bold]")

    if config["type"] == "CLI tool":
        config["framework"] = questionary.select(
            "CLI framework:",
            choices=["Click", "Typer", "argparse"],
        ).ask()
    elif config["type"] == "Web service":
        config["framework"] = questionary.select(
            "Web framework:",
            choices=["FastAPI", "Flask", "Starlette"],
        ).ask()
    else:
        config["framework"] = None

    if config.get("framework") is None and config["type"] in ("CLI tool", "Web service"):
        return {}

    # Phase 3: Confirmation
    console.print()
    console.print("[bold]Step 3 of 3: Confirm[/bold]")
    console.print()

    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column("Key", style="bold")
    summary.add_column("Value")
    for k, v in config.items():
        if v is not None:
            summary.add_row(k.replace("_", " ").title(), str(v))

    console.print(summary)
    console.print()

    if not questionary.confirm("Create project with these settings?", default=True).ask():
        return {}

    return config
```

## Handling Cancellation

Always handle `None` returns (user pressed Ctrl-C or Escape).

```python
import sys
import questionary

result = questionary.select("Choose:", choices=["a", "b", "c"]).ask()
if result is None:
    console.print("[dim]Cancelled.[/dim]")
    sys.exit(0)
```

## Dynamic Width for Choices

If you must compute choice widths (for alignment within choices), do it once from the data, not from terminal width.

```python
def format_choices(items: list[dict]) -> list[questionary.Choice]:
    """Align choice fields based on data width, not terminal width."""
    # Compute max width from data
    max_name = max(len(item["name"]) for item in items) if items else 0

    choices = []
    for item in items:
        # Pad based on data, not terminal
        title = f"{item['name']:<{max_name}}  {item['count']} sessions"
        choices.append(questionary.Choice(title=title, value=item["id"]))

    return choices
```

This is acceptable because the padding is derived from the data itself, not from terminal width calculations with magic numbers. The terminal handles overflow naturally.

## Combining Rich and Questionary

The key rule: Rich handles display, Questionary handles input. Do not try to use Rich markup inside Questionary choice titles (it will render as plain text with brackets).

```python
# Wrong: Rich markup in Questionary
choice = questionary.Choice(title="[green]active[/green] my-app")
# User sees: [green]active[/green] my-app

# Right: plain text in Questionary, Rich for context display
console.print("[green]active[/green] projects:")
choice = questionary.Choice(title="my-app (active)")
```
