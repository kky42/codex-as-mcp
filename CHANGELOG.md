# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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