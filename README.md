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

# Custom timeout (default 300s)
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest --timeout 600

# Writable mode with auto approve (dangerous)
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest --yolo --auto-approve
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
- `codex_execute(prompt, work_dir, model?)` - General purpose codex execution
- `codex_review(review_type, work_dir, target?, prompt?, model?)` - Specialized code review

### Specify model

Both tools 支持可选的 `model` 参数，用于选择 Codex 模型。当前暂时可选模型：

```log
▌  1. gpt-5 minimal  — fastest responses with limited reasoning; ideal for coding, instructions, or lightweight tasks
▌  2. gpt-5 low  — balances speed with some reasoning; useful for straightforward queries and short explanations
▌> 3. gpt-5 medium (current)  — default setting; provides a solid balance of reasoning depth and latency for general-purpose tasks
▌  4. gpt-5 high  — maximizes reasoning depth for complex or ambiguous problems
```

传入其他模型将提示不支持并回退到 Codex 默认模型。

```bash
# 指定模型执行代码
claude mcp call codex codex_execute '{"prompt":"print(1)","work_dir":"/path","model":"gpt-5 high"}'

# 指定模型进行代码审查
claude mcp call codex codex_review '{"review_type":"staged","work_dir":"/path","model":"gpt-5 low"}'
```

If you have any other use case requirements, feel free to open issue.

## Review Prompt Configuration

Default review templates are stored in `review_prompts.yaml` at the project root. You can edit this file or add new review scenarios:

```yaml
security: |
  You are an expert code reviewer focusing on security aspects.
  {custom_prompt}
```

Invoke it with:

```python
codex_review("security", work_dir, target)
```

## Safety

- **Safe Mode**: Default read-only operations protect your environment
- **Writable Mode**: Use `--yolo` flag when you need full codex capabilities
- **Sequential Execution**: Prevents conflicts from parallel agent operations
 - **Auto Approval**: `--auto-approve` skips all confirmation prompts. ⚠️ May execute destructive actions without warning.
