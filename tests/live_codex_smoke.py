"""Optional live Codex integration smoke test.

This is intentionally not part of the default pytest suite. It requires a real
Codex-compatible provider and API key, and is meant for a manually triggered
GitHub Actions workflow or a maintainer machine.
"""

import asyncio
import os
import tempfile
from pathlib import Path

from codex_as_mcp import server


class DummyContext:
    async def report_progress(self, *args, **kwargs):
        return None


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


async def main() -> None:
    api_key = require_env("CODEX_LIVE_API_KEY")
    base_url = require_env("CODEX_LIVE_BASE_URL")
    model = require_env("CODEX_LIVE_MODEL")
    provider = os.environ.get("CODEX_LIVE_PROVIDER", "live_provider")
    env_key = os.environ.get("CODEX_LIVE_ENV_KEY", "CODEX_LIVE_API_KEY")
    wire_api = os.environ.get("CODEX_LIVE_WIRE_API", "responses")

    with tempfile.TemporaryDirectory(prefix="codex-live-home-") as codex_home, tempfile.TemporaryDirectory(
        prefix="codex-as-mcp-live-work-"
    ) as workdir:
        Path(codex_home, "config.toml").write_text(
            f'''
model = "{model}"
model_provider = "{provider}"
approval_policy = "never"
sandbox_mode = "read-only"

[model_providers.{provider}]
name = "{provider}"
base_url = "{base_url}"
env_key = "{env_key}"
wire_api = "{wire_api}"
requires_openai_auth = false
'''.lstrip(),
            encoding="utf-8",
        )

        old_cwd = os.getcwd()
        old_codex_home = os.environ.get("CODEX_HOME")
        old_key = os.environ.get(env_key)
        try:
            os.environ["CODEX_HOME"] = codex_home
            os.environ[env_key] = api_key
            os.chdir(workdir)

            prompt = (
                "Reply with exactly this single token and nothing else: "
                "CODEX_AS_MCP_LIVE_OK"
            )
            result = await asyncio.wait_for(server.spawn_agent(DummyContext(), prompt), timeout=180)
            print(result)
            if "CODEX_AS_MCP_LIVE_OK" not in result:
                raise SystemExit("Live Codex smoke test did not return the expected token")
        finally:
            os.chdir(old_cwd)
            if old_codex_home is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = old_codex_home
            if old_key is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = old_key


if __name__ == "__main__":
    asyncio.run(main())
