"""
Minimal MCP server (v2) exposing a single tool: `spawn_agent`.

Tool: spawn_agent(prompt: str, work_directory: str) -> str
- Runs the Codex CLI agent and returns its final response as the tool result.

Command executed:
    codex e --cd {work_directory} --skip-git-repo-check --full-auto {prompt}

Notes:
- No Authorization headers or extra auth flows are used.
- Uses a generous default timeout to allow long-running agent sessions.
- Designed to be run via: `uv run python -m codex_as_mcp`
"""

import asyncio
import shutil
import subprocess
import time
import tempfile
import os

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
async def spawn_agent(ctx: Context, prompt: str, work_directory: str) -> str:
    """Spawn a Codex agent to work inside a directory.

    Args:
        prompt: All instructions/context the agent needs for the task.
        work_directory: Absolute path to the working directory for the task.

    Returns:
        The agent's final response (clean output from Codex CLI).
    """
    # Basic validation to avoid confusing UI errors
    if not isinstance(prompt, str) or not isinstance(work_directory, str):
        return "Error: 'prompt' and 'work_directory' must be strings."
    if not prompt.strip():
        return "Error: 'prompt' is required and cannot be empty."
    if not work_directory.strip():
        return "Error: 'work_directory' is required and cannot be empty."

    try:
        codex_exec = _resolve_codex_executable()
    except FileNotFoundError as e:
        return f"Error: {e}"

    # Create temp file for clean output
    # Codex CLI detects non-TTY and outputs only the final response
    temp_fd, temp_path = tempfile.mkstemp(suffix=".txt", prefix="codex_output_")
    
    try:
        # Quote the prompt so Codex CLI receives it wrapped in "..."
        quoted_prompt = '"' + prompt.replace('"', '\\"') + '"'

        cmd = [
            codex_exec,
            "e",
            "--cd",
            work_directory,
            "--skip-git-repo-check",
            "--full-auto",
            quoted_prompt,
        ]

        # Initial progress ping
        try:
            await ctx.report_progress(0, None, "Launching Codex agent...")
        except Exception:
            pass

        # Run with stdout redirected to temp file
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=temp_fd,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            return f"Error: Failed to launch Codex agent: {e}"

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

        # Read the clean output from temp file
        with open(temp_path, "r") as f:
            output = f.read().strip()

        if returncode != 0:
            # Read stderr for error details
            stderr = ""
            if proc.stderr:
                stderr_bytes = await proc.stderr.read()
                stderr = stderr_bytes.decode(errors="replace")
            
            return (
                "Error: Codex agent exited with a non-zero status.\n"
                f"Command: {' '.join(cmd)}\n"
                f"Exit Code: {returncode}\n"
                f"Stderr: {stderr}\n"
                f"Output: {output}"
            )

        return output

    finally:
        # Clean up temp file
        try:
            os.close(temp_fd)
            os.unlink(temp_path)
        except Exception:
            pass


@mcp.tool()
async def spawn_agents_parallel(
    ctx: Context,
    agents: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Spawn multiple Codex agents in parallel.

    Args:
        agents: List of agent specs, each with 'prompt' and 'work_directory'.
                Example: [
                    {"prompt": "Create math.md", "work_directory": "/path/to/dir"},
                    {"prompt": "Create story.md", "work_directory": "/path/to/dir"}
                ]

    Returns:
        List of results with 'index', 'output', and optional 'error' fields.
    """
    if not isinstance(agents, list):
        return [{"index": "0", "error": "Error: 'agents' must be a list of agent specs"}]

    if not agents:
        return [{"index": "0", "error": "Error: 'agents' list cannot be empty"}]

    async def run_one(index: int, spec: dict) -> dict:
        """Run a single agent and return result with index."""
        try:
            # Validate spec
            if not isinstance(spec, dict):
                return {
                    "index": str(index),
                    "error": f"Agent {index}: spec must be a dictionary with 'prompt' and 'work_directory'"
                }

            prompt = spec.get("prompt", "")
            work_directory = spec.get("work_directory", "")

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
            output = await spawn_agent(ctx, prompt, work_directory)

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
