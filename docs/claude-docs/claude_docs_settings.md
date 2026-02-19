|  |  |  |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | API key sent as `X-Api-Key` header, typically for the Claude SDK (for interactive usage, run `/login`) |  |
| `ANTHROPIC_AUTH_TOKEN` | Custom value for the `Authorization` header (the value you set here will be prefixed with `Bearer` ) |  |
| `ANTHROPIC_CUSTOM_HEADERS` | Custom headers to add to requests (`Name: Value` format, newline-separated for multiple headers) |  |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | See [Model configuration](https://code.claude.com/docs/en/model-config#environment-variables) |  |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | See [Model configuration](https://code.claude.com/docs/en/model-config#environment-variables) |  |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | See [Model configuration](https://code.claude.com/docs/en/model-config#environment-variables) |  |
| `ANTHROPIC_FOUNDRY_API_KEY` | API key for Microsoft Foundry authentication (see [Microsoft Foundry](https://code.claude.com/docs/en/microsoft-foundry)) |  |
| `ANTHROPIC_FOUNDRY_BASE_URL` | Full base URL for the Foundry resource (for example, `https://my-resource.services.ai.azure.com/anthropic`). Alternative to `ANTHROPIC_FOUNDRY_RESOURCE` (see [Microsoft Foundry](https://code.claude.com/docs/en/microsoft-foundry)) |  |
| `ANTHROPIC_FOUNDRY_RESOURCE` | Foundry resource name (for example, `my-resource`). Required if `ANTHROPIC_FOUNDRY_BASE_URL` is not set (see [Microsoft Foundry](https://code.claude.com/docs/en/microsoft-foundry)) |  |
| `ANTHROPIC_MODEL` | Name of the model setting to use (see [Model Configuration](https://code.claude.com/docs/en/model-config#environment-variables)) |  |
| `ANTHROPIC_SMALL_FAST_MODEL` | [DEPRECATED] Name of [Haiku-class model for background tasks](https://code.claude.com/docs/en/costs) |  |
| `ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION` | Override AWS region for the Haiku-class model when using Bedrock |  |
| `AWS_BEARER_TOKEN_BEDROCK` | Bedrock API key for authentication (see [Bedrock API keys](https://aws.amazon.com/blogs/machine-learning/accelerate-ai-development-with-amazon-bedrock-api-keys/)) |  |
| `BASH_DEFAULT_TIMEOUT_MS` | Default timeout for long-running bash commands |  |
| `BASH_MAX_OUTPUT_LENGTH` | Maximum number of characters in bash outputs before they are middle-truncated |  |
| `BASH_MAX_TIMEOUT_MS` | Maximum timeout the model can set for long-running bash commands |  |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Set the percentage of context capacity (1-100) at which auto-compaction triggers. By default, auto-compaction triggers at approximately 95% capacity. Use lower values like `50` to compact earlier. Values above the default threshold have no effect. Applies to both main conversations and subagents. This percentage aligns with the `context_window.used_percentage` field available in [status line](https://code.claude.com/docs/en/statusline) |  |
| `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` | Return to the original working directory after each Bash command |  |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | Set to `1` to load CLAUDE.md files from directories specified with `--add-dir`. By default, additional directories do not load memory files | `1` |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | Set to `1` to enable [agent teams](https://code.claude.com/docs/en/agent-teams). Agent teams are experimental and disabled by default |  |
| `CLAUDE_CODE_API_KEY_HELPER_TTL_MS` | Interval in milliseconds at which credentials should be refreshed (when using `apiKeyHelper`) |  |
| `CLAUDE_CODE_CLIENT_CERT` | Path to client certificate file for mTLS authentication |  |
| `CLAUDE_CODE_CLIENT_KEY_PASSPHRASE` | Passphrase for encrypted CLAUDE\_CODE\_CLIENT\_KEY (optional) |  |
| `CLAUDE_CODE_CLIENT_KEY` | Path to client private key file for mTLS authentication |  |
| `CLAUDE_CODE_EFFORT_LEVEL` | Set the effort level for supported models. Values: `low`, `medium`, `high` (default). Lower effort is faster and cheaper, higher effort provides deeper reasoning. Currently supported with Opus 4.6 only. See [Adjust effort level](https://code.claude.com/docs/en/model-config#adjust-effort-level) |  |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | Set to `1` to disable Anthropic API-specific `anthropic-beta` headers. Use this if experiencing issues like “Unexpected value(s) for the `anthropic-beta` header” when using an LLM gateway with third-party providers |  |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | Set to `1` to disable [auto memory](https://code.claude.com/docs/en/memory#auto-memory). Set to `0` to force auto memory on during the gradual rollout. When disabled, Claude does not create or load auto memory files |  |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | Set to `1` to disable all background task functionality, including the `run_in_background` parameter on Bash and subagent tools, auto-backgrounding, and the Ctrl+B shortcut |  |
| `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY` | Set to `1` to disable the “How is Claude doing?” session quality surveys. Also disabled when using third-party providers or when telemetry is disabled. See [Session quality surveys](https://code.claude.com/docs/en/data-usage#session-quality-surveys) |  |
| `CLAUDE_CODE_EXIT_AFTER_STOP_DELAY` | Time in milliseconds to wait after the query loop becomes idle before automatically exiting. Useful for automated workflows and scripts using SDK mode |  |
| `CLAUDE_CODE_PROXY_RESOLVES_HOSTS` | Set to `true` to allow the proxy to perform DNS resolution instead of the caller. Opt-in for environments where the proxy should handle hostname resolution |  |
| `CLAUDE_CODE_TASK_LIST_ID` | Share a task list across sessions. Set the same ID in multiple Claude Code instances to coordinate on a shared task list. See [Task list](https://code.claude.com/docs/en/interactive-mode#task-list) |  |
| `CLAUDE_CODE_TEAM_NAME` | Name of the agent team this teammate belongs to. Set automatically on [agent team](https://code.claude.com/docs/en/agent-teams) members |  |
| `CLAUDE_CODE_TMPDIR` | Override the temp directory used for internal temp files. Claude Code appends `/claude/` to this path. Default: `/tmp` on Unix/macOS, `os.tmpdir()` on Windows |  |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | Equivalent of setting `DISABLE_AUTOUPDATER`, `DISABLE_BUG_COMMAND`, `DISABLE_ERROR_REPORTING`, and `DISABLE_TELEMETRY` |  |
| `CLAUDE_CODE_DISABLE_TERMINAL_TITLE` | Set to `1` to disable automatic terminal title updates based on conversation context |  |
| `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` | Set to `false` to disable prompt suggestions (the “Prompt suggestions” toggle in `/config`). These are the grayed-out predictions that appear in your prompt input after Claude responds. See [Prompt suggestions](https://code.claude.com/docs/en/interactive-mode#prompt-suggestions) |  |
| `CLAUDE_CODE_ENABLE_TASKS` | Set to `false` to temporarily revert to the previous TODO list instead of the task tracking system. Default: `true`. See [Task list](https://code.claude.com/docs/en/interactive-mode#task-list) |  |
| `CLAUDE_CODE_ENABLE_TELEMETRY` | Set to `1` to enable OpenTelemetry data collection for metrics and logging. Required before configuring OTel exporters. See [Monitoring](https://code.claude.com/docs/en/monitoring-usage) |  |
| `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | Override the default token limit for file reads. Useful when you need to read larger files in full |  |
| `CLAUDE_CODE_HIDE_ACCOUNT_INFO` | Set to `1` to hide your email address and organization name from the Claude Code UI. Useful when streaming or recording |  |
| `CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL` | Skip auto-installation of IDE extensions |  |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Set the maximum number of output tokens for most requests. Default: 32,000. Maximum: 64,000. Increasing this value reduces the effective context window available before [auto-compaction](https://code.claude.com/docs/en/costs#reduce-token-usage) triggers. |  |
| `CLAUDE_CODE_OTEL_HEADERS_HELPER_DEBOUNCE_MS` | Interval for refreshing dynamic OpenTelemetry headers in milliseconds (default: 1740000 / 29 minutes). See [Dynamic headers](https://code.claude.com/docs/en/monitoring-usage#dynamic-headers) |  |
| `CLAUDE_CODE_PLAN_MODE_REQUIRED` | Auto-set to `true` on [agent team](https://code.claude.com/docs/en/agent-teams) teammates that require plan approval. Read-only: set by Claude Code when spawning teammates. See [require plan approval](https://code.claude.com/docs/en/agent-teams#require-plan-approval-for-teammates) |  |
| `CLAUDE_CODE_SHELL` | Override automatic shell detection. Useful when your login shell differs from your preferred working shell (for example, `bash` vs `zsh`) |  |
| `CLAUDE_CODE_SHELL_PREFIX` | Command prefix to wrap all bash commands (for example, for logging or auditing). Example: `/path/to/logger.sh` will execute `/path/to/logger.sh <command>` |  |
| `CLAUDE_CODE_SKIP_BEDROCK_AUTH` | Skip AWS authentication for Bedrock (for example, when using an LLM gateway) |  |
| `CLAUDE_CODE_SKIP_FOUNDRY_AUTH` | Skip Azure authentication for Microsoft Foundry (for example, when using an LLM gateway) |  |
| `CLAUDE_CODE_SKIP_VERTEX_AUTH` | Skip Google authentication for Vertex (for example, when using an LLM gateway) |  |
| `CLAUDE_CODE_SUBAGENT_MODEL` | See [Model configuration](https://code.claude.com/docs/en/model-config) |  |
| `CLAUDE_CODE_USE_BEDROCK` | Use [Bedrock](https://code.claude.com/docs/en/amazon-bedrock) |  |
| `CLAUDE_CODE_USE_FOUNDRY` | Use [Microsoft Foundry](https://code.claude.com/docs/en/microsoft-foundry) |  |
| `CLAUDE_CODE_USE_VERTEX` | Use [Vertex](https://code.claude.com/docs/en/google-vertex-ai) |  |
| `CLAUDE_CONFIG_DIR` | Customize where Claude Code stores its configuration and data files |  |
| `DISABLE_AUTOUPDATER` | Set to `1` to disable automatic updates. |  |
| `DISABLE_BUG_COMMAND` | Set to `1` to disable the `/bug` command |  |
| `DISABLE_COST_WARNINGS` | Set to `1` to disable cost warning messages |  |
| `DISABLE_ERROR_REPORTING` | Set to `1` to opt out of Sentry error reporting |  |
| `DISABLE_INSTALLATION_CHECKS` | Set to `1` to disable installation warnings. Use only when manually managing the installation location, as this can mask issues with standard installations |  |
| `DISABLE_NON_ESSENTIAL_MODEL_CALLS` | Set to `1` to disable model calls for non-critical paths like flavor text |  |
| `DISABLE_PROMPT_CACHING` | Set to `1` to disable prompt caching for all models (takes precedence over per-model settings) |  |
| `DISABLE_PROMPT_CACHING_HAIKU` | Set to `1` to disable prompt caching for Haiku models |  |
| `DISABLE_PROMPT_CACHING_OPUS` | Set to `1` to disable prompt caching for Opus models |  |
| `DISABLE_PROMPT_CACHING_SONNET` | Set to `1` to disable prompt caching for Sonnet models |  |
| `DISABLE_TELEMETRY` | Set to `1` to opt out of Statsig telemetry (note that Statsig events do not include user data like code, file paths, or bash commands) |  |
| `ENABLE_TOOL_SEARCH` | Controls [MCP tool search](https://code.claude.com/docs/en/mcp#scale-with-mcp-tool-search). Values: `auto` (default, enables at 10% context), `auto:N` (custom threshold, e.g., `auto:5` for 5%), `true` (always on), `false` (disabled) |  |
| `FORCE_AUTOUPDATE_PLUGINS` | Set to `true` to force plugin auto-updates even when the main auto-updater is disabled via `DISABLE_AUTOUPDATER` |  |
| `HTTP_PROXY` | Specify HTTP proxy server for network connections |  |
| `HTTPS_PROXY` | Specify HTTPS proxy server for network connections |  |
| `IS_DEMO` | Set to `true` to enable demo mode: hides email and organization from the UI, skips onboarding, and hides internal commands. Useful for streaming or recording sessions |  |
| `MAX_MCP_OUTPUT_TOKENS` | Maximum number of tokens allowed in MCP tool responses. Claude Code displays a warning when output exceeds 10,000 tokens (default: 25000) |  |
| `MAX_THINKING_TOKENS` | Override the [extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) token budget. Thinking is enabled at max budget (31,999 tokens) by default. Use this to limit the budget (for example, `MAX_THINKING_TOKENS=10000`) or disable thinking entirely (`MAX_THINKING_TOKENS=0`). For Opus 4.6, thinking depth is controlled by [effort level](https://code.claude.com/docs/en/model-config#adjust-effort-level) instead, and this variable is ignored unless set to `0` to disable thinking. |  |
| `MCP_CLIENT_SECRET` | OAuth client secret for MCP servers that require [pre-configured credentials](https://code.claude.com/docs/en/mcp#use-pre-configured-oauth-credentials). Avoids the interactive prompt when adding a server with `--client-secret` |  |
| `MCP_OAUTH_CALLBACK_PORT` | Fixed port for the OAuth redirect callback, as an alternative to `--callback-port` when adding an MCP server with [pre-configured credentials](https://code.claude.com/docs/en/mcp#use-pre-configured-oauth-credentials) |  |
| `MCP_TIMEOUT` | Timeout in milliseconds for MCP server startup |  |
| `MCP_TOOL_TIMEOUT` | Timeout in milliseconds for MCP tool execution |  |
| `NO_PROXY` | List of domains and IPs to which requests will be directly issued, bypassing proxy |  |
| `SLASH_COMMAND_TOOL_CHAR_BUDGET` | Override the character budget for skill metadata shown to the [Skill tool](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill). The budget scales dynamically at 2% of the context window, with a fallback of 16,000 characters. Legacy name kept for backwards compatibility |  |
| `USE_BUILTIN_RIPGREP` | Set to `0` to use system-installed `rg` instead of `rg` included with Claude Code |  |
| `VERTEX_REGION_CLAUDE_3_5_HAIKU` | Override region for Claude 3.5 Haiku when using Vertex AI |  |
| `VERTEX_REGION_CLAUDE_3_7_SONNET` | Override region for Claude 3.7 Sonnet when using Vertex AI |  |
| `VERTEX_REGION_CLAUDE_4_0_OPUS` | Override region for Claude 4.0 Opus when using Vertex AI |  |
| `VERTEX_REGION_CLAUDE_4_0_SONNET` | Override region for Claude 4.0 Sonnet when using Vertex AI |  |
| `VERTEX_REGION_CLAUDE_4_1_OPUS` | Override region for Claude 4.1 Opus when using Vertex AI |  |