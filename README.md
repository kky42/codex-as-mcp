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

Or use Claude Code commands:
```bash
# Safe mode (default)
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest

# Writable mode
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest --yolo
```

### 3. Customize environment

Copy the provided `env.config.json` and adjust dependencies, interpreter path or virtual env location as needed:

```bash
cp env.config.json my-env.json
# edit my-env.json to change python version, packages, python_path or venv_path
```

Set `python_path` to the full path of a local interpreter (e.g., `F:\python310\python.exe` on Windows) and `venv_path` to where the virtual environment should be created. Running `main.py` will read `env.config.json` to create/activate that environment and install listed packages. If the file is missing, it falls back to `uv.lock`.

## Tools

The MCP server exposes two tools:
- `codex_execute(prompt, work_dir)` - General purpose codex execution
- `codex_review(review_type, work_dir, target?, prompt?)` - Specialized code review

If you have any other use case requirements, feel free to open issue.

## Safety

- **Safe Mode**: Default read-only operations protect your environment
- **Writable Mode**: Use `--yolo` flag when you need full codex capabilities
- **Sequential Execution**: Prevents conflicts from parallel agent operations
