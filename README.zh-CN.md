# codex-as-mcp

**通过 Codex-as-MCP 生成多个子代理**

每个子代理在指定目录中以完全自主的方式运行 `codex e --full-auto`。非常适合 Plus/Pro/Team 订阅用户使用 GPT-5 能力。

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

- `spawn_agent(prompt, work_directory)` - 在指定目录中生成自主 Codex 子代理
- `spawn_agents_parallel(agents)` - 并行生成多个 Codex 子代理。接受包含 `prompt` 和 `work_directory` 字段的代理规格列表
