# Verification Patterns for Environment Forge

Database state comparison methodology for verifying agent task completion. Each task gets a verification function that examines the database before and after agent execution.

## Core Concept

Verification = deterministic check of database state change.

```
initial.db  -->  [agent executes task via tools]  -->  current.db
    |                                                       |
    +----->  verify_task(initial_db, final_db)  <-----------+
                         |
                    pass / fail + diagnostics
```

The agent is given tasks to complete using the environment's MCP tools. After execution, verification functions compare database state to determine whether the task was actually completed.

## Verification Strategies

### Modification-Based (CREATE, UPDATE, DELETE tasks)

Compare initial vs final database to detect expected changes.

```python
def verify_add_product_to_cart(initial_db_path: str, final_db_path: str) -> dict:
    import sqlite3

    conn_initial = sqlite3.connect(initial_db_path)
    conn_final = sqlite3.connect(final_db_path)

    # Count cart items before and after
    initial_count = conn_initial.execute(
        "SELECT COUNT(*) FROM cart_items WHERE user_id = 1"
    ).fetchone()[0]

    final_count = conn_final.execute(
        "SELECT COUNT(*) FROM cart_items WHERE user_id = 1"
    ).fetchone()[0]

    # Check what was added
    new_items = conn_final.execute("""
        SELECT ci.id, p.name, p.price, ci.quantity
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.user_id = 1
        AND ci.id NOT IN (
            SELECT id FROM cart_items WHERE user_id = 1
        )
    """).fetchall()

    # Note: the subquery above references the same DB.
    # For proper diff, query both databases:
    initial_cart_ids = set(
        r[0] for r in conn_initial.execute(
            "SELECT id FROM cart_items WHERE user_id = 1"
        ).fetchall()
    )
    final_cart_ids = set(
        r[0] for r in conn_final.execute(
            "SELECT id FROM cart_items WHERE user_id = 1"
        ).fetchall()
    )
    new_ids = final_cart_ids - initial_cart_ids

    conn_initial.close()
    conn_final.close()

    return {
        "initial_cart_count": initial_count,
        "final_cart_count": final_count,
        "items_added": final_count - initial_count,
        "new_item_ids": list(new_ids),
        "task_completed": final_count > initial_count
    }
```

### Query-Based (READ, SEARCH, LIST tasks)

For tasks that ask the agent to find or report information, verification checks whether the agent's answer matches what the database actually contains.

```python
def verify_find_cheapest_laptop(
    initial_db_path: str,
    final_db_path: str,
    final_answer: str | None = None,
) -> dict:
    import sqlite3
    import re

    conn = sqlite3.connect(final_db_path)

    # What the correct answer should be
    cheapest = conn.execute("""
        SELECT name, price FROM products
        WHERE LOWER(name) LIKE '%laptop%' OR LOWER(category) = 'electronics'
        ORDER BY price ASC LIMIT 1
    """).fetchone()

    conn.close()

    result = {
        "expected_product": cheapest[0] if cheapest else None,
        "expected_price": cheapest[1] if cheapest else None,
    }

    if final_answer and cheapest:
        # Check if the answer mentions the correct product
        name_match = cheapest[0].lower() in final_answer.lower()
        price_match = str(cheapest[1]) in final_answer
        result["name_mentioned"] = name_match
        result["price_mentioned"] = price_match
        result["task_completed"] = name_match or price_match
    else:
        result["task_completed"] = False

    return result
```

### Combined (multi-step tasks)

Tasks that require both action and reporting. Verify BOTH database changes AND answer content.

```python
def verify_search_and_add_to_cart(
    initial_db_path: str,
    final_db_path: str,
    final_answer: str | None = None,
) -> dict:
    import sqlite3

    conn_initial = sqlite3.connect(initial_db_path)
    conn_final = sqlite3.connect(final_db_path)

    # Verify cart was modified (action part)
    initial_count = conn_initial.execute(
        "SELECT COUNT(*) FROM cart_items WHERE user_id = 1"
    ).fetchone()[0]
    final_count = conn_final.execute(
        "SELECT COUNT(*) FROM cart_items WHERE user_id = 1"
    ).fetchone()[0]

    # Check what was added matches search criteria
    new_items = conn_final.execute("""
        SELECT p.name, p.price FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.user_id = 1
    """).fetchall()

    conn_initial.close()
    conn_final.close()

    cart_changed = final_count > initial_count
    # Check if cheapest was selected
    added_cheapest = False
    if new_items:
        prices = [item[1] for item in new_items]
        added_cheapest = min(prices) == prices[-1]  # last added should be cheapest

    return {
        "cart_items_added": final_count - initial_count,
        "cart_changed": cart_changed,
        "items_in_cart": [{"name": n, "price": p} for n, p in new_items],
        "task_completed": cart_changed
    }
```

## Verification Function Contract

Every verification function follows this signature:

```python
def verify_<task_name>(
    initial_db_path: str,
    final_db_path: str,
    final_answer: str | None = None,
) -> dict:
    """
    Args:
        initial_db_path: Path to SQLite DB before agent action
        final_db_path: Path to SQLite DB after agent action
        final_answer: Optional text answer from agent (for query tasks)

    Returns:
        dict with:
        - Diagnostic fields (what was checked, what was found)
        - "task_completed": bool indicating pass/fail
    """
```

### Rules

1. Use `sqlite3` library only (standard library)
2. NEVER modify either database -- read only
3. Return a dict that can be JSON serialized (no tuples as keys, no datetime objects)
4. Include diagnostic fields, not just pass/fail -- the diagnostics help debug failures
5. Handle edge cases: empty tables, missing records, null values
6. Close connections before returning

## Running Verification

### Snapshot Pattern

Before agent execution:
```bash
# Create snapshot of initial state
cp .env-forge/environments/<name>/db/current.db .env-forge/environments/<name>/db/initial.db
```

After agent execution:
```python
import importlib.util

# Load verifiers module
spec = importlib.util.spec_from_file_location("verifiers", "verifiers.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Run specific verifier
result = mod.verify_task_0("db/initial.db", "db/current.db")
print(result)
```

### Reset Pattern

To re-run a task from clean state:
```bash
cp .env-forge/environments/<name>/db/initial.db .env-forge/environments/<name>/db/current.db
```

## Verification Coverage by Task Type

| Task Pattern | Strategy | Key Checks |
|-------------|----------|------------|
| "Add X to Y" | Modification | Row count increased, correct FK references |
| "Create a new X" | Modification | New row exists with expected field values |
| "Update X to Y" | Modification | Specific fields changed to expected values |
| "Delete X" | Modification | Row no longer exists, cascades handled |
| "Find X" | Query | Answer contains correct entity/value |
| "List all X" | Query | Answer contains expected count/entities |
| "Get total/count of X" | Query | Answer matches aggregation result |
| "Search for X and do Y" | Combined | Both DB change and answer content verified |

## Strictness Levels

### Strict (code-based judge)
Return `{"result": "complete"}` only when 100% certain ALL conditions met. Any uncertainty returns `{"result": "others"}`.

### Diagnostic (LLM-as-a-judge)
Return rich diagnostic dict. A separate LLM evaluates whether the diagnostics indicate task completion. More forgiving of partial completion.

For forge-generated environments, prefer the diagnostic approach -- it provides more useful feedback during development and testing.
