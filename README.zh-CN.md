# codex-as-mcp

**通过 Codex-as-MCP 生成多个子代理**

每个子代理都会在 MCP 服务器当前工作目录中以完全自主的方式运行 `codex e --full-auto`。非常适合 Plus/Pro/Team 订阅用户使用 GPT-5 能力。

**在 Claude Code 中使用**

codex-as-mcp 包含两个工具：
![tools](assets/tools.png)

你可以通过 prompt 并行启动多个 Codex 子代理：
![alt text](assets/claude.png)

下图展示了并行委派两个任务的 Codex 会话示例：
![Codex 使用示例](assets/codex.png)

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

如果直接配置 Codex CLI（例如 `~/.config/codex/config.toml`），可以添加：
```toml
[mcp_servers.subagents]
command = "uvx"
args = ["codex-as-mcp@latest"]
```

## 工具

- `spawn_agent(prompt: str)` – 在服务器的工作目录内生成自主 Codex 子代理，并返回代理的最终消息。
- `spawn_agents_parallel(agents: list[dict])` – 并行生成多个 Codex 子代理；每个元素需要包含 `prompt` 字段，返回值会按索引给出每个子代理的 `output`（最终消息）或 `error`。

## Provider 凭证（`env_key`）

如果你的 `~/.codex/config.toml`（或 `~/.config/codex/config.toml`）里某个 provider 配置了 `env_key`，Codex CLI 运行时会从环境变量里读取对应的 Key。

示例：
```toml
model_provider = "custom_provider"

[model_providers.custom_provider]
name = "custom_provider"
base_url = "https://..."
wire_api = "responses"
env_key = "PROVIDER_API_KEY"
show_raw_agent_reasoning = true
```

请确保 MCP server 进程拥有该环境变量，这样它才能把变量透传给其启动的 `codex` 子进程。
环境变量名必须与上面的 `env_key` 值一致（这里是 `PROVIDER_API_KEY`）。

**方式 A（推荐）：在 MCP 客户端配置里设置 env（如果支持）**
```json
{
  "mcpServers": {
    "codex-subagent": {
      "type": "stdio",
      "command": "uvx",
      "args": ["codex-as-mcp@latest"],
      "env": {
        "PROVIDER_API_KEY": "KEY_VALUE"
      }
    }
  }
}
```

**方式 B：通过 server 启动参数传入 env**
```bash
uvx codex-as-mcp@latest --env PROVIDER_API_KEY=KEY_VALUE
```

**方式 C：通过 Codex CLI（`codex mcp add`）添加**
```bash
codex mcp add codex-subagent --env PROVIDER_API_KEY=KEY_VALUE -- uvx codex-as-mcp@latest
```

安全提示：把密钥写在命令行参数里，可能会在本机进程列表中可见；优先使用方式 A。
