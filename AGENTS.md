- use uv to manage dependency
- run command with uv like `uv run ...`
- i've set up the pypi token with bash variable "PYPI_TOKEN", source ~/.bashrc or ~/.zshrc first
- implement base on `https://github.com/modelcontextprotocol/python-sdk`

## Testing Local MCP Server

### Start MCP Inspector Web UI
```bash
npx @modelcontextprotocol/inspector
```

This will:
- Start Inspector at `http://localhost:6274`
- Provide authentication token in URL
- Open browser automatically

### Configure Server Connection in Inspector
- **Transport Type**: STDIO
- **Command**: `uv`
- **Arguments**: `["run", "python", "-m", "codex_as_mcp"]`
- **Working Directory**: `/Users/kky/Projects/codex-as-mcp`

### Available Tools to Test
- **`codex_execute`**: Execute prompts using codex for general purpose
- **`codex_review`**: Specialized code review (files, staged, unstaged, changes, pr, general)

### Server Modes
- Default: Safe mode (read-only)
- Writable mode: Add `--yolo` flag

## Note
- You are using zsh terminal