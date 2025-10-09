"""Allow running the MCP server as a module with python -m codex_as_mcp

This entrypoint launches the minimal server implementation in src/codex_as_mcp/server.py.
"""

from .server import main

if __name__ == "__main__":
    main()
