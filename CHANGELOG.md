# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Send Codex prompts through stdin using `codex e ... -` and close the pipe, preventing Windows MCP tool-call hangs caused by inherited JSON-RPC stdin and avoiding command-line prompt truncation/quoting issues.

### Added
- Add GitHub Actions CI across Linux, macOS, and Windows for Python 3.11 and 3.12.
- Add regression tests for stdin prompt delivery and stdin write failure handling.
- Add an optional manually triggered live Codex smoke workflow gated by `CODEX_LIVE_API_KEY` for maintainers with a Responses-compatible provider.

## [2026.2.2.1] - 2026-02-02

### 🛠️ Fixed
- Spawned Codex runs now use `--dangerously-bypass-approvals-and-sandbox` by default (fixes #7).

## [2026.1.14.3] - 2026-01-14

### 🔄 Changed
- Roll back the codebase to the `8cdf8bd` implementation and republish a new version.

## [2026.1.14.4] - 2026-01-14

### ➕ Added
- Support passing provider credentials/env vars through the MCP server to spawned Codex CLI processes:
  - Server-level defaults via `--env KEY=VALUE` (repeatable)

### 📚 Documentation
- Document `env_key` behavior and include examples for Claude Code, `uvx`, and `codex mcp add --env`.

## [2026.1.14.5] - 2026-01-14

### 🔄 Changed
- README now includes a concrete third-party provider `config.toml` example and shows adding the MCP with `PROVIDER_API_KEY=...` when `env_key="PROVIDER_API_KEY"`.

### 🧹 Removed
- Removed the tool-level `env` parameter; credentials are provided when launching the MCP server (environment), not by tool callers.

## [2025.10.20.1] - 2025-10-20

### 📚 Documentation
- Align README, README.zh-CN, and AGENTS tool docs with current `spawn_agent`/`spawn_agents_parallel` behavior.

### 🔢 Versioning
- Release `2025.10.20.1` and publish to PyPI.

## [2025.9.16] - 2025-09-16

### 🛠️ Fixed
- Replace console emojis with ASCII labels to prevent UnicodeEncodeError on Windows (GBK) terminals.

## [2025.9.4] - 2025-09-03

### 🛠️ Fixed
- **Windows Compatibility**: Fixed `[WinError 2] 系统找不到指定的文件` (system cannot find file) error on Windows
- Added cross-platform executable resolution using `shutil.which()` 
- Enhanced error handling with `FileNotFoundError` catching in both `codex_execute` and `codex_review`
- Improved error messages with Windows-specific guidance and installation instructions

### 🔧 Changed  
- Added platform detection to provide Windows-specific error messages
- Enhanced subprocess command resolution for cross-platform compatibility
- Updated error handling to guide Windows users to proper installation steps or WSL usage

### 📚 Documentation
- Windows users now receive helpful error messages about experimental support
- Added guidance for npm installation and PATH configuration
- Included WSL recommendation for better Windows compatibility

## [0.1.16] - 2025-08-28

### 🛠️ Fixed
- **BREAKING**: Fixed "list index out of range" error in codex_execute and codex_review functions
- Added comprehensive defensive checks for empty codex output blocks
- Enhanced error handling with detailed diagnostic information
- Improved subprocess handling to capture output even on command failures

### 🔧 Changed
- **BREAKING**: Updated command structure to use only two modes:
  - **Default mode**: `--sandbox read-only --ask-for-approval never` (safe for all operations)
  - **YOLO mode**: `--dangerously-bypass-approvals-and-sandbox` (full access with --yolo flag)
- Removed unsupported `--skip-git-repo-check` and `--full-auto` flags
- **BREAKING**: Now requires Codex CLI version >= 0.25.0

### 📚 Documentation
- Added prominent version requirement warnings in README files
- Updated installation instructions to use `@latest` tag
- Added version verification steps
- Emphasized compatibility requirements

### 🧪 Internal
- Enhanced error messages with command details and output previews
- Added explicit IndexError handling alongside existing ValueError handling
- Improved CalledProcessError handling with captured output

## [0.1.15] - Previous Release

### Features
- Safe mode implementation with read-only sandbox
- Writable mode with --yolo flag
- Sequential execution to prevent conflicts
- Two main tools: codex_execute and codex_review

---

## Migration Guide for v0.1.16

### Breaking Changes

1. **Codex CLI Version**: Update to version 0.25.0 or later:
   ```bash
   npm install -g @openai/codex@latest
   codex --version  # Verify >= 0.25.0
   ```

2. **Command Flags**: The server now uses different internal flags:
   - Old: `--full-auto --skip-git-repo-check`
   - New: `--dangerously-bypass-approvals-and-sandbox` (converted to read-only in safe mode)

3. **Error Handling**: Improved error messages may look different but provide more diagnostic information

### What Stays the Same

- MCP server configuration in `.mcp.json` remains unchanged
- Tool signatures (`codex_execute` and `codex_review`) remain the same
- Safe mode vs YOLO mode behavior is unchanged
- All documented features work the same way

### Benefits

- ✅ Eliminates "list index out of range" crashes
- ✅ Better error diagnostics for troubleshooting
- ✅ More robust command execution
- ✅ Compatible with latest Codex CLI features
