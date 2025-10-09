# codex-as-mcp

[中文版](./README.zh-CN.md)

**MCP server for delegating tasks to Codex CLI subagents.**

Spawn autonomous Codex agents from Claude Desktop, Cursor, or any MCP-compatible AI tool. Each subagent runs `codex e --full-auto` with complete autonomy in a specified directory. Perfect for Plus/Pro/Team subscribers leveraging GPT-5 capabilities.

## Setup

### 1. Install Codex CLI

**⚠️ Requires Codex CLI >= 0.46.0**

```bash
npm install -g @openai/codex@latest
codex login

# Verify installation
codex --version
```

### 2. Configure MCP

Add to your `.mcp.json`:
```json
{
  "mcpServers": {
    "codex": {
      "type": "stdio",
      "command": "uvx",
      "args": ["codex-as-mcp@latest"]
    }
  }
}
```

Or use Claude Desktop commands:
```bash
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest
```

## Tool

- `spawn_agent(prompt, work_directory)` - Spawns an autonomous Codex subagent in the specified directory

## How It Works

The MCP server spawns Codex CLI subagents using `codex e --full-auto`, providing complete task autonomy. Each subagent receives your prompt and executes independently within the specified directory.

## Local test
```shell
uv run mcp dev src/codex_as_mcp/server.py
```