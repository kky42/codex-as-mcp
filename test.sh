#!/usr/bin/env bash
set -euo pipefail

# Simple helper to start the MCP Inspector wired to THIS repo's minimal server.
# Default: launches Inspector + local MCP via `uv run mcp dev src/codex_as_mcp/server.py`.
# Optional: --ui-only (see usage below).

usage() {
  cat <<'USAGE'
Usage:
  ./test.sh               Start Inspector + local dev MCP (server_v2)
  ./test.sh --ui-only     Only start Inspector (manually add server in UI)
  ./test.sh --cleanup-ports [--yes]
                          Kill any process listening on ports 6274/6277

Notes:
- This script uses uv for dependencies and zsh/bash profile for env.
- It runs the LOCAL server file `src/codex_as_mcp/server.py` (not a released package).
USAGE
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command '$1' not found in PATH" >&2
    exit 1
  fi
}

# Port helpers (macOS compatible)
is_port_in_use() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

list_port_procs() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
}

kill_port_procs() {
  local port="$1"
  # extract PIDs and kill
  local pids
  pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | sort -u || true)
  if [ -n "$pids" ]; then
    echo "Killing PIDs on port $port: $pids"
    kill $pids 2>/dev/null || true
    sleep 0.3
    # force kill any remaining
    pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | sort -u || true)
    if [ -n "$pids" ]; then
      echo "Force killing PIDs on port $port: $pids"
      kill -9 $pids 2>/dev/null || true
    fi
  fi
}

# Load user shells (as requested) so PATH/TOKENs are available
[ -f "$HOME/.zshrc" ] && . "$HOME/.zshrc" || true
[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc" || true

# Validate repo layout
REPO_ROOT=$(pwd)
SERVER_FILE="$REPO_ROOT/src/codex_as_mcp/server.py"
if [ ! -f "$SERVER_FILE" ]; then
  echo "Error: $SERVER_FILE not found. Run from the repo root." >&2
  exit 1
fi

# Ensure core tools
require_cmd uv

MODE="default"
AUTO_YES="no"
if [ "${1-}" = "--help" ] || [ "${1-}" = "-h" ]; then
  usage; exit 0
elif [ "${1-}" = "--ui-only" ]; then
  MODE="ui-only"
elif [ "${1-}" = "--cleanup-ports" ]; then
  MODE="cleanup"
elif [ -n "${1-}" ]; then
  echo "Unknown option: $1" >&2
  usage; exit 2
fi

if [ "$MODE" = "cleanup" ]; then
  if [ "${2-}" = "--yes" ]; then AUTO_YES="yes"; fi
  echo "Checking Inspector ports (UI 6274, Proxy 6277)..."
  for PORT in 6274 6277; do
    if is_port_in_use "$PORT"; then
      echo "Port $PORT is in use by:"
      list_port_procs "$PORT"
      if [ "$AUTO_YES" != "yes" ]; then
        read -r -p "Kill processes on port $PORT? [y/N] " ans
        case "$ans" in
          y|Y|yes|YES) ;;
          *) echo "Skipped port $PORT"; continue;;
        esac
      fi
      kill_port_procs "$PORT"
      if is_port_in_use "$PORT"; then
        echo "Warning: port $PORT still in use after attempts."
      else
        echo "Port $PORT cleared."
      fi
    else
      echo "Port $PORT is free."
    fi
  done
  exit 0
fi

case "$MODE" in
  default)
    # Preflight: fail fast if ports busy (Inspector uses these)
    if is_port_in_use 6277; then
      echo "Error: Proxy Server PORT IS IN USE at port 6277" >&2
      echo "Hint: ./test.sh --cleanup-ports to free it, or close any running Inspector." >&2
      exit 3
    fi
    if is_port_in_use 6274; then
      echo "Warning: Inspector UI port 6274 is in use. The dev command may fail or reuse it." >&2
      echo "Hint: ./test.sh --cleanup-ports to free it, or close any running Inspector." >&2
    fi
    echo "Starting MCP Inspector + LOCAL dev server using mcp dev..."
    echo "  Repo:    $REPO_ROOT"
    echo "  Command: uv run mcp dev src/codex_as_mcp/server.py"
    echo
    # Increase Inspector request timeouts and enable progress-based resets
    export MCP_SERVER_REQUEST_TIMEOUT=${MCP_SERVER_REQUEST_TIMEOUT:-300000}
    export MCP_REQUEST_TIMEOUT_RESET_ON_PROGRESS=${MCP_REQUEST_TIMEOUT_RESET_ON_PROGRESS:-true}
    export MCP_REQUEST_MAX_TOTAL_TIMEOUT=${MCP_REQUEST_MAX_TOTAL_TIMEOUT:-28800000}
    # mcp dev launches the Inspector web UI and runs the given LOCAL Python file.
    exec uv run mcp dev "$SERVER_FILE"
    ;;
  ui-only)
    require_cmd npx
    if is_port_in_use 6277; then
      echo "Error: Proxy Server PORT IS IN USE at port 6277" >&2
      echo "Hint: ./test.sh --cleanup-ports to free it, or close any running Inspector." >&2
      exit 3
    fi
    echo "Starting MCP Inspector only (no server started yet)..."
    echo "In the web UI, add a STDIO server with:" 
    echo "  Command: uv"
    echo "  Args:    [\"run\", \"python\", \"-m\", \"codex_as_mcp\"]"
    echo "  CWD:     $REPO_ROOT"
    echo
    export MCP_SERVER_REQUEST_TIMEOUT=${MCP_SERVER_REQUEST_TIMEOUT:-300000}
    export MCP_REQUEST_TIMEOUT_RESET_ON_PROGRESS=${MCP_REQUEST_TIMEOUT_RESET_ON_PROGRESS:-true}
    export MCP_REQUEST_MAX_TOTAL_TIMEOUT=${MCP_REQUEST_MAX_TOTAL_TIMEOUT:-28800000}
    exec npx @modelcontextprotocol/inspector
    ;;
esac
