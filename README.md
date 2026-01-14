# codex-as-mcp

[中文版](./README.zh-CN.md)

`codex-as-mcp` is a small **Model Context Protocol (MCP)** server that lets MCP clients (Claude Code, Cursor, etc.) delegate work to the **Codex CLI**.

It exposes two tools that run Codex in the server's current working directory:
- `spawn_agent(prompt: str, env?: dict[str, str])`
- `spawn_agents_parallel(agents: list[dict])`

Under the hood, each agent runs something like:
`codex exec --cd <server cwd> --skip-git-repo-check --full-auto "<prompt>"`.

Note: `--full-auto` means the agent can run commands and edit files in that directory. Use this server only in repos you trust.

## Use it in Claude Code

There are two tools in codex-as-mcp
![tools](assets/tools.png)

You can spawn parallel codex subagents using prompt.
![alt text](assets/claude.png)

Here's a sample Codex session delegating two tasks in parallel.
![Codex use case](assets/codex.png)

## Quick start

### 1. Install Codex CLI

**Requires Codex CLI >= 0.46.0**

```bash
npm install -g @openai/codex@latest
codex login

# Verify installation
codex --version
```

Make sure Codex CLI can run non-interactively on your machine (provider + credentials in `~/.codex/config.toml`, or via the provider-specific env var it references).

### Provider credentials (`env_key`)

If your `~/.codex/config.toml` (or `~/.config/codex/config.toml`) provider config uses an `env_key`, Codex CLI expects that env var to be present when it runs.

Example:
```toml
[model_providers.your_provider]
name = "your_provider"
base_url = "https://your-provider.example/v1"
wire_api = "responses"
env_key = "YOUR_ENV_KEY_NAME"
```

Make sure the MCP server process has that env var set, so it can pass it through to the spawned `codex` process. The env var name **must match** the `env_key` value above.

**Option A (recommended): set env in your MCP client config (if supported)**
```json
{
  "mcpServers": {
    "codex-subagent": {
      "type": "stdio",
      "command": "uvx",
      "args": ["codex-as-mcp@latest"],
      "env": {
        "YOUR_ENV_KEY_NAME": "KEY_VALUE"
      }
    }
  }
}
```

**Option B: pass env via server args**
```bash
uvx codex-as-mcp@latest --env YOUR_ENV_KEY_NAME=KEY_VALUE
```

**Option C: add via Codex CLI (`codex mcp add`)**
```bash
codex mcp add codex-subagent --env YOUR_ENV_KEY_NAME=KEY_VALUE -- uvx codex-as-mcp@latest
```

Security note: passing secrets via command-line args may be visible via process lists on your machine; prefer option A when possible.

### 2. Configure MCP

Add to your `.mcp.json`:
```json
{
  "mcpServers": {
    "codex-subagent": {
      "type": "stdio",
      "command": "uvx",
      "args": ["codex-as-mcp@latest"]
    }
  }
}
```

Or use Claude Desktop commands:
```bash
claude mcp add codex-subagent -- uvx codex-as-mcp@latest
```

If you're configuring Codex CLI directly (for example `~/.config/codex/config.toml`), add:
```toml
[mcp_servers.subagents]
command = "uvx"
args = ["codex-as-mcp@latest"]
```

## Tools

- `spawn_agent(prompt: str, env?: dict[str, str])` – Spawns an autonomous Codex subagent using the server's working directory and returns the agent's final message. Use `env` to pass provider credentials (the env var name must match `env_key` in Codex config.toml) if your MCP client cannot set server-level environment variables.
- `spawn_agents_parallel(agents: list[dict])` – Spawns multiple Codex subagents in parallel; each item must include a `prompt` key and may include `env`; results include either an `output` or an `error` per agent.
