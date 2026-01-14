"""Allow running the MCP server as a module with python -m codex_as_mcp

This entrypoint launches the minimal server implementation in src/codex_as_mcp/server.py.
"""

import argparse

from . import server


def _parse_env_kv(pair: str) -> tuple[str, str]:
    if "=" not in pair:
        raise ValueError(f"Invalid --env value '{pair}'. Expected KEY=VALUE.")
    key, value = pair.split("=", 1)
    if not key:
        raise ValueError(f"Invalid --env value '{pair}'. KEY must be non-empty.")
    return key, value


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="codex-as-mcp", add_help=True)
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Set env var(s) for spawned Codex CLI processes (repeatable). "
            "Useful for provider credentials (the env var name must match your provider's "
            "`env_key` in Codex config.toml)."
        ),
    )

    args, _unknown = parser.parse_known_args(argv)

    overrides: dict[str, str] = {}
    for pair in args.env:
        key, value = _parse_env_kv(pair)
        overrides[key] = value

    if overrides:
        server.set_default_child_env(overrides)

    server.main()

if __name__ == "__main__":
    main()
