# codex-as-mcp

**通过 Codex CLI 子代理委派任务的 MCP 服务器。**

从 Claude Desktop、Cursor 或任何 MCP 兼容的 AI 工具生成自主 Codex 代理。每个子代理在指定目录中以完全自主的方式运行 `codex e --full-auto`。非常适合 Plus/Pro/Team 订阅用户使用 GPT-5 能力。

## 安装与配置

### 1. 安装 Codex CLI

**⚠️ 需要 Codex CLI >= 0.46.0**

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

## 工作原理

MCP 服务器使用 `codex e --full-auto` 生成 Codex CLI 子代理，提供完全的任务自主权。每个子代理接收你的提示并在指定目录中独立执行。

## 本地测试
```shell
uv run mcp dev src/codex_as_mcp/server.py
```
