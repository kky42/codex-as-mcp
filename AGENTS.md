- use uv to manage dependency
- run command with uv like `uv run ...`
- i've set up the pypi token /user with environment variable "PYPI_TOKEN" and "PYPI_USERNAME", source ~/.bashrc or ~/.zshrc first
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

If you see quick request timeouts, increase Inspector timeouts or use `test.sh` which exports:
- `MCP_SERVER_REQUEST_TIMEOUT=300000`
- `MCP_REQUEST_TIMEOUT_RESET_ON_PROGRESS=true`
- `MCP_REQUEST_MAX_TOTAL_TIMEOUT=28800000`

### Available Tools to Test
- **`spawn_agent`**: Run Codex agent inside a directory and return its stdout

Inputs:
- `prompt` (string): Everything the agent should know/do.
- `work_directory` (string): Absolute path where the agent works.

Behavior:
- Executes: `codex e --cd <work_directory> --skip-git-repo-check --full-auto "<prompt>"`
- Wraps the prompt in quotes; escapes inner quotes.
- Sends periodic progress heartbeats so Inspector won’t time out.

### Server Modes
- Single mode: always writable (Codex edits files in `work_directory`).
  Use with care and run inside the intended project folder.

## Building and Publishing to PyPI

### Prerequisites
- PyPI credentials are set as environment variables: `PYPI_TOKEN` and `PYPI_USERNAME`
- Source the environment: `source ~/.zshrc` (or `~/.bashrc`)

### Steps to Publish

1. **Update version number** in `pyproject.toml`:
   ```toml
   [project]
   version = "YYYY.MM.DD.N"  # e.g., "2025.10.9.1"
   ```

2. **Build the package**:
   ```bash
   cd /Users/kky/Projects/codex-as-mcp
   rm -rf dist/
   uv build
   ```
   This generates:
   - `dist/codex_as_mcp-{version}.tar.gz`
   - `dist/codex_as_mcp-{version}-py3-none-any.whl`

3. **Publish to PyPI**:
   ```bash
   twine upload dist/* --username "$PYPI_USERNAME" --password "$PYPI_TOKEN" --non-interactive
   ```

4. **Verify publication**:
   - Check: https://pypi.org/project/codex-as-mcp/
   - Install: `uvx codex-as-mcp@latest`

## Note
- You are using zsh terminal
