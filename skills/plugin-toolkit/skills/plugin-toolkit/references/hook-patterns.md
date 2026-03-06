# Hook Patterns

Common patterns for Claude Code plugin hooks.

---

## Hook Types

| Event | When Triggered | Common Uses |
|-------|----------------|-------------|
| `UserPromptSubmit` | Before user message processed | Context injection, validation |
| `PreToolUse` | Before a tool is called | Tool modification, logging |
| `PostToolUse` | After a tool completes | Result processing, cleanup |
| `SessionStart` | When session begins | Initialization, welcome messages |

---

## hooks.json Structure

```json
{
  "description": "Description of what these hooks do",
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "regex pattern",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/script.sh"
          }
        ]
      }
    ]
  }
}
```

---

## Common Patterns

### Always-On Injection

Inject context with every message:

```json
{
  "matcher": ".*",
  "hooks": [{
    "type": "command",
    "command": "${CLAUDE_PLUGIN_ROOT}/hooks/inject.sh"
  }]
}
```

**Important**: Always provide opt-out mechanism when using this pattern.

### Command-Specific Hooks

Trigger only for specific commands:

```json
{
  "matcher": "^/mycommand",
  "hooks": [{
    "type": "command",
    "command": "${CLAUDE_PLUGIN_ROOT}/hooks/handle-mycommand.sh"
  }]
}
```

### Multiple Matchers with Priority

Earlier matchers take priority:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "^/plugin:off",
        "hooks": [{ "type": "command", "command": "...disable.sh" }]
      },
      {
        "matcher": "^/plugin:on",
        "hooks": [{ "type": "command", "command": "...enable.sh" }]
      },
      {
        "matcher": ".*",
        "hooks": [{ "type": "command", "command": "...inject.sh" }]
      }
    ]
  }
}
```

---

## Hook Scripts

### Basic Template

```bash
#!/bin/bash
set -e

# Your hook logic here

# Output goes to Claude as context
echo "Context to inject"
```

### With Disabled State Check

```bash
#!/bin/bash
set -e

MARKER_FILE="$HOME/.cache/plugin-name/disabled"
if [ -f "$MARKER_FILE" ]; then
  exit 0
fi

# Rest of hook logic
```

### Enable/Disable Scripts

**disable.sh:**
```bash
#!/bin/bash
set -e

MARKER_DIR="$HOME/.cache/plugin-name"
mkdir -p "$MARKER_DIR"
touch "$MARKER_DIR/disabled"
```

**enable.sh:**
```bash
#!/bin/bash
set -e

MARKER_FILE="$HOME/.cache/plugin-name/disabled"
[ -f "$MARKER_FILE" ] && rm "$MARKER_FILE"
exit 0
```

---

## Opt-Out Pattern

Every auto-activating plugin should implement this pattern:

### 1. Add disable/enable commands

```
commands/
├── off.md
└── on.md
```

### 2. Add hook handlers

```
hooks/
├── hooks.json
├── disable.sh
├── enable.sh
└── inject.sh
```

### 3. Update hooks.json

Put specific matchers before catch-all:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "matcher": "^/plugin:off", "hooks": [...] },
      { "matcher": "^/plugin:on", "hooks": [...] },
      { "matcher": ".*", "hooks": [...] }
    ]
  }
}
```

### 4. Check state in inject script

```bash
#!/bin/bash
set -e

if [ -f "$HOME/.cache/plugin-name/disabled" ]; then
  exit 0
fi

# Normal injection
cat << 'EOF'
...
EOF
```

---

## Error Handling

### Always Use set -e

```bash
#!/bin/bash
set -e  # Exit on any error
```

### Handle Missing Dependencies

```bash
#!/bin/bash
set -e

if ! command -v jq &> /dev/null; then
  echo "Warning: jq not installed, some features unavailable"
  exit 0
fi
```

### Graceful Degradation

```bash
#!/bin/bash
set -e

CONFIG_FILE="$HOME/.config/plugin/config.json"
if [ -f "$CONFIG_FILE" ]; then
  # Use config
  SETTING=$(jq -r '.setting' "$CONFIG_FILE")
else
  # Use defaults
  SETTING="default"
fi
```

---

## Testing Hooks

### Manual Test

```bash
# Run hook script directly
./hooks/inject.sh

# Check exit code
echo $?
```

### Verify Registration

```bash
# Check hooks.json is valid JSON
cat hooks/hooks.json | jq .
```

### Test Matcher Patterns

```bash
# Test regex patterns
echo "/plugin:off" | grep -E "^/plugin:off"
```
