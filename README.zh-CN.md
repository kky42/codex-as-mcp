# codex-as-mcp

**通过 Codex-as-MCP 生成多个子代理**

每个子代理都会在 MCP 服务器当前工作目录中以完全自主的方式运行 `codex e --full-auto`。非常适合 Plus/Pro/Team 订阅用户使用 GPT-5 能力。

**在 Claude Code 中使用**

codex-as-mcp 包含两个工具：
![tools](assets/tools.png)

你可以通过 prompt 并行启动多个 Codex 子代理：
![alt text](assets/delegation_subagents.png)

## 安装

### 1. 安装 Codex CLI

**需要 Codex CLI >= 0.46.0**

```bash
npm install -g @openai/codex@latest
codex login

# 验证安装
codex --version
```

### 2. 配置 MCP

在 `.mcp.json` 中添加：
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

或者使用 Claude Desktop 命令：
```bash
claude mcp add codex-subagent -- uvx codex-as-mcp@latest
```

## 工具

- `spawn_agent(prompt: str)` – 在服务器的工作目录内生成自主 Codex 子代理，并返回代理的最终消息。
- `spawn_agents_parallel(agents: list[dict])` – 并行生成多个 Codex 子代理；每个元素需要包含 `prompt` 字段，返回值会按索引给出每个子代理的 `output`（最终消息）或 `error`。
