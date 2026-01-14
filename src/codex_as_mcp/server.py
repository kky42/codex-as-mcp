"""
Minimal MCP server (v2) exposing a single tool: `spawn_agent`.

Tool: spawn_agent(prompt: str) -> str
- Runs the Codex CLI agent and returns its final response as the tool result.

Command executed:
    codex e --cd {os.getcwd()} --skip-git-repo-check --full-auto \
        --output-last-message {temp_output} "{prompt}"

Notes:
- No Authorization headers or extra auth flows are used.
- Uses a generous default timeout to allow long-running agent sessions.
- Designed to be run via: `uv run python -m codex_as_mcp`
"""

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Context


# Default timeout (seconds) for the spawned agent run.
# Chosen to be long to accommodate non-trivial editing tasks.
DEFAULT_TIMEOUT_SECONDS: int = 8 * 60 * 60  # 8 hours


mcp = FastMCP("codex-subagent")


def _resolve_codex_executable() -> str:
    """Resolve the `codex` executable path or raise a clear error.

    Returns:
        str: Absolute path to the `codex` executable.

    Raises:
        FileNotFoundError: If the executable cannot be found in PATH.
    """
    codex = shutil.which("codex")
    if not codex:
        raise FileNotFoundError(
            "Codex CLI not found in PATH. Please install it (e.g. `npm i -g @openai/codex`) "
            "and ensure your shell PATH includes the npm global bin."
        )
    return codex


@mcp.tool()
async def spawn_agent(ctx: Context, prompt: str) -> str:
    """Spawn a Codex agent to work inside the current working directory.

    The server resolves the working directory via ``os.getcwd()`` so it inherits
    whatever environment the MCP process currently has.

    Args:
        prompt: All instructions/context the agent needs for the task.

    Returns:
        The agent's final response (clean output from Codex CLI).
    """
    # Basic validation to avoid confusing UI errors
    if not isinstance(prompt, str):
        return "Error: 'prompt' must be a string."
    if not prompt.strip():
        return "Error: 'prompt' is required and cannot be empty."

    try:
        codex_exec = _resolve_codex_executable()
    except FileNotFoundError as e:
        return f"Error: {e}"

    work_directory = os.getcwd()

    with tempfile.TemporaryDirectory(prefix="codex_output_") as temp_dir:
        output_path = Path(temp_dir) / "last_message.md"
        output_path.touch()

        # Quote the prompt so Codex CLI receives it wrapped in "..."
        quoted_prompt = '"' + prompt.replace('"', '\\"') + '"'

        cmd = [
            codex_exec,
            "e",
            "--cd",
            work_directory,
            "--skip-git-repo-check",
            "--full-auto",
            "--output-last-message",
            str(output_path),
            quoted_prompt,
        ]

        # Initial progress ping
        try:
            await ctx.report_progress(0, None, "Launching Codex agent...")
        except Exception:
            pass

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            return f"Error: Failed to launch Codex agent: {e}"

        stdout_task = asyncio.create_task(proc.stdout.read()) if proc.stdout else None
        stderr_task = asyncio.create_task(proc.stderr.read()) if proc.stderr else None

        # Send periodic heartbeats while process runs
        last_ping = time.monotonic()
        while True:
            try:
                returncode = await asyncio.wait_for(proc.wait(), timeout=2.0)
                break
            except asyncio.TimeoutError:
                now = time.monotonic()
                if now - last_ping >= 2.0:
                    last_ping = now
                    try:
                        await ctx.report_progress(1, None, "Codex agent running...")
                    except Exception:
                        pass

        stdout = ""
        if stdout_task:
            stdout_bytes = await stdout_task
            stdout = stdout_bytes.decode(errors="replace")

        stderr = ""
        if stderr_task:
            stderr_bytes = await stderr_task
            stderr = stderr_bytes.decode(errors="replace")

        output = output_path.read_text(encoding="utf-8").strip()

        if returncode != 0:
            details = [
                "Error: Codex agent exited with a non-zero status.",
                f"Command: {' '.join(cmd)}",
                f"Exit Code: {returncode}",
            ]
            if stderr:
                details.append(f"Stderr: {stderr}")
            if stdout:
                details.append(f"Stdout: {stdout}")
            if output:
                details.append(f"Captured Output: {output}")
            return "\n".join(details)

        return output


@mcp.tool()
async def spawn_agents_parallel(
    ctx: Context,
    agents: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Spawn multiple Codex agents in parallel.

    Each spawned agent reuses the server's current working directory
    (``os.getcwd()``).

    Args:
        agents: List of agent specs, each with a 'prompt' entry.
                Example: [
                    {"prompt": "Create math.md"},
                    {"prompt": "Create story.md"}
                ]

    Returns:
        List of results with 'index', 'output', and optional 'error' fields.
    """
    if not isinstance(agents, list):
        return [{"index": "0", "error": "Error: 'agents' must be a list of agent specs."}]

    if not agents:
        return [{"index": "0", "error": "Error: 'agents' list cannot be empty."}]

    async def run_one(index: int, spec: dict) -> dict:
        """Run a single agent and return result with index."""
        try:
            # Validate spec
            if not isinstance(spec, dict):
                return {
                    "index": str(index),
                    "error": f"Agent {index}: spec must be a dictionary with a 'prompt' field."
                }

            prompt = spec.get("prompt", "")

            # Report progress for this agent
            try:
                await ctx.report_progress(
                    index,
                    len(agents),
                    f"Starting agent {index + 1}/{len(agents)}..."
                )
            except Exception:
                pass

            # Run the agent
            output = await spawn_agent(ctx, prompt)

            # Check if output contains an error
            if output.startswith("Error:"):
                return {"index": str(index), "error": output}

            return {"index": str(index), "output": output}

        except Exception as e:
            return {"index": str(index), "error": f"Agent {index}: {str(e)}"}

    # Run all agents concurrently
    tasks = [run_one(i, agent) for i, agent in enumerate(agents)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions that weren't caught
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append({"index": str(i), "error": f"Unexpected error: {str(result)}"})
        else:
            final_results.append(result)

    return final_results


def main() -> None:
    """Entry point for the MCP server v2."""
    mcp.run()


if __name__ == "__main__":
    main()
