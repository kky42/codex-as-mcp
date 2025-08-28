# codex-as-mcp

[中文版](./README.zh-CN.md)

Enable Claude Code, Cursor and other AI tools to call Codex for task execution. Plus/Pro/Team subscribers can maximize GPT-5 usage without additional costs.

## Setup

### 1. Install Codex CLI

**⚠️ Requires Codex CLI version >= 0.25.0**

```bash
npm install -g @openai/codex@latest
codex login

# Verify version
codex --version
```

> **Important**: This MCP server uses `--sandbox` and `--ask-for-approval` flags that require Codex CLI v0.25.0 or later. Earlier versions are not supported.

### 2. Configure MCP

Add to your `.mcp.json`:
**Safe Mode (Default):**
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

**Writable Mode:**
```json
{
  "mcpServers": {
    "codex": {
      "type": "stdio",
      "command": "uvx",
      "args": ["codex-as-mcp@latest", "--yolo"]
    }
  }
}
```

**Writable Mode with Auto Approval (dangerous):**
```json
{
  "mcpServers": {
    "codex": {
      "type": "stdio",
      "command": "uvx",
      "args": ["codex-as-mcp@latest", "--yolo", "--auto-approve"]
    }
  }
}
```

Or use Claude Code commands:
```bash
# Safe mode (default)
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest

# Writable mode
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest --yolo

# Writable mode with auto approve (dangerous)
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest --yolo --auto-approve
```

## Tools

The MCP server exposes two tools:
- `codex_execute(prompt, work_dir)` - General purpose codex execution
- `codex_review(review_type, work_dir, target?, prompt?)` - Specialized code review

If you have any other use case requirements, feel free to open issue.

## Safety

- **Safe Mode**: Default read-only operations protect your environment
- **Writable Mode**: Use `--yolo` flag when you need full codex capabilities
- **Auto Approval**: `--auto-approve` skips all confirmation prompts. ⚠️ May execute destructive actions without warning.
- **Sequential Execution**: Prevents conflicts from parallel agent operations