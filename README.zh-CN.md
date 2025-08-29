# codex-as-mcp

让 Claude Code、Cursor 等 AI 工具调用 Codex 执行任务。Plus/Pro/Team 订阅用户可在不增加额外费用的情况下最大化使用 GPT-5。

## 安装与配置

### 1. 安装 Codex CLI

**⚠️ 需要 Codex CLI 版本 >= 0.25.0**

```bash
npm install -g @openai/codex@latest
codex login

# 验证版本
codex --version
```

> **重要**: 此 MCP 服务器使用需要 Codex CLI v0.25.0 或更高版本的 `--sandbox` 和 `--ask-for-approval` 标志。不支持早期版本。

### 2. 配置 MCP

在 `.mcp.json` 中添加：
【安全模式（默认）】
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

【可写模式】
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

【可写模式并自动同意（危险）】
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

或者使用 Claude Code 命令：
```bash
# 安全模式（默认）
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest

# 可写模式
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest --yolo

# 自定义超时（默认 300 秒）
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest --timeout 600

# 可写模式并自动同意（危险）
claude mcp add codex-as-mcp -- uvx codex-as-mcp@latest --yolo --auto-approve
```

### 3. 自定义环境

复制根目录的 `env.config.json` 并根据需要调整依赖、解释器路径或虚拟环境位置：

```bash
cp env.config.json my-env.json
# 编辑 my-env.json 修改 Python 版本、依赖、python_path 或 venv_path
```

将 `python_path` 设置为本地解释器的完整路径（如 Windows 上的 `F:\python310\python.exe`），并将 `venv_path` 指向希望创建虚拟环境的位置。运行 `main.py` 时会优先读取 `env.config.json` 创建/激活该环境并安装依赖；若文件不存在则回退到 `uv.lock`。

## 工具

MCP 服务器暴露两个工具：
- `codex_execute(prompt, work_dir, model?)`：通用的 Codex 执行
- `codex_review(review_type, work_dir, target?, prompt?, model?)`：专项代码审查

### 指定模型

两个工具均支持可选的 `model` 参数，用于选择 Codex 模型。当前暂时可选模型：

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

如有其他使用场景需求，欢迎提交 issue。

## 自定义 Review 场景

默认的 review 模板存放在项目根目录的 `review_prompts.yaml` 中。你可以修改此文件或新增场景，例如：

```yaml
security: |
  专注于安全漏洞的代码审查。
  {custom_prompt}
```

然后使用：

```python
codex_review("security", work_dir, target)
```

## 安全性

- 安全模式：默认只读操作，保护你的环境
- 可写模式：需要完整能力时使用 `--yolo` 标志
- 自动同意：使用 `--auto-approve` 跳过所有确认。⚠️ 可能执行具有破坏性的操作，谨慎使用
- 顺序执行：避免多代理并行操作产生冲突

