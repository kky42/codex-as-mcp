from mcp.server.fastmcp import FastMCP, Context
import subprocess
import re
import argparse
import sys
import shutil
import platform
from typing import List, Dict, Optional, Sequence

# Global safe mode setting
SAFE_MODE = True

mcp = FastMCP("codex-as-mcp")

HEADER_RE = re.compile(
    r'^'
    r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]'   # 1: timestamp
    r'\s+'
    r'([^\n]+)'                                    # 2: tag (整行，允许包含空格/冒号)
    r'\n',
    flags=re.M
)

BLOCK_RE = re.compile(
    r'^'
    r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]\s+([^\n]+)\n'  # 1: ts, 2: tag
    r'(.*?)'                                                   # 3: body
    r'(?=^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\]\s+[^\n]+\n|\Z)',
    flags=re.M | re.S
)

def run_and_extract_codex_blocks(
    cmd: Sequence[str],
    tags: Optional[Sequence[str]] = ("codex",),
    last_n: int = 1,
    safe_mode: bool = True
) -> List[Dict[str, str]]:
    """
    运行命令并抽取日志块。每个块由形如
    [YYYY-MM-DDTHH:MM:SS] <tag>
    <正文...直到下一个时间戳头或文件结束>
    组成。

    :param cmd: 完整命令（列表形式）
    :param tags: 需要过滤的 tag 列表（大小写不敏感）。None 表示不过滤。
    :param last_n: 返回最后 N 个匹配块
    :return: [{timestamp, tag, body, raw}] 按时间顺序（旧->新）
    :raises ValueError: 当没有找到匹配的日志块时
    :raises subprocess.CalledProcessError: 当命令执行失败时
    """
    # Resolve executable path for cross-platform compatibility
    final_cmd = list(cmd)
    if final_cmd and final_cmd[0] == "codex":
        codex_executable = shutil.which("codex")
        if not codex_executable:
            # Provide helpful error message for Windows users
            is_windows = platform.system().lower() == "windows"
            error_msg = "Codex CLI not found in PATH. "
            if is_windows:
                error_msg += (
                    "Windows support is experimental. Please:\n"
                    "1. Ensure Codex CLI is installed: npm install -g @openai/codex\n"
                    "2. Add the npm global bin directory to PATH\n"
                    "3. Or consider using WSL for better compatibility"
                )
            else:
                error_msg += "Please install Codex CLI: npm install -g @openai/codex"
            raise FileNotFoundError(error_msg)
        final_cmd[0] = codex_executable
    
    # Modify command based on safe mode
    if safe_mode:
        # Replace --dangerously-bypass-approvals-and-sandbox with read-only mode
        if "--dangerously-bypass-approvals-and-sandbox" in final_cmd:
            idx = final_cmd.index("--dangerously-bypass-approvals-and-sandbox")
            final_cmd[idx:idx+1] = ["--sandbox", "read-only"]
    
    proc = subprocess.run(
        final_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
    )
    out = proc.stdout
    
    # Check for non-zero exit code and raise with captured output
    if proc.returncode != 0:
        error = subprocess.CalledProcessError(proc.returncode, final_cmd, output=out)
        error.stdout = out
        raise error

    blocks = []
    for m in BLOCK_RE.finditer(out):
        ts, tag, body = m.group(1), m.group(2).strip(), m.group(3)
        if tags is None or tag.lower() in {t.lower() for t in tags}:
            raw = f'[{ts}] {tag}\n{body}'
            blocks.append({"timestamp": ts, "tag": tag, "body": body, "raw": raw})

    if not blocks:
        # Include command and output snippet for debugging
        cmd_str = " ".join(final_cmd)
        output_preview = (out[:200] + "..." if len(out) > 200 else out) if out else "(no output)"
        raise ValueError(f"No matching codex blocks found in command output.\nCommand: {cmd_str}\nOutput preview: {output_preview}")
    
    # 只取最后 1 个
    return blocks[-last_n:]


# Pre-defined review prompts for different scenarios
REVIEW_PROMPTS = {
    "files": """You are an expert code reviewer. Please conduct a thorough code review of the specified files.

Focus on:
- Code quality and best practices
- Potential bugs and security issues
- Performance considerations
- Maintainability and readability
- Design patterns and architecture

Files to review: {target}

{custom_prompt}

Please provide detailed feedback with specific suggestions for improvement.""",

    "staged": """You are an expert code reviewer. Please review the staged changes (git diff --cached) that are ready to be committed.

Focus on:
- Code quality and adherence to best practices
- Potential bugs introduced by the changes
- Security vulnerabilities
- Performance impact
- Breaking changes or compatibility issues
- Commit readiness

{custom_prompt}

Please provide feedback on whether these changes are ready for commit and any improvements needed.""",

    "unstaged": """You are an expert code reviewer. Please review the unstaged changes (git diff) in the working directory.

Focus on:
- Code quality and best practices
- Potential bugs and issues
- Incomplete implementations
- Code style and formatting
- Areas that need attention before staging

{custom_prompt}

Please provide feedback on the current changes and what should be addressed before committing.""",

    "changes": """You are an expert code reviewer. Please review the git changes in the specified commit range.

Focus on:
- Overall impact and coherence of the changes
- Code quality and best practices
- Potential regressions or bugs
- Security implications
- Performance impact
- Documentation needs

Commit range: {target}

{custom_prompt}

Please provide comprehensive feedback on these changes.""",

    "pr": """You are an expert code reviewer. Please conduct a comprehensive pull request review.

Focus on:
- Overall design and architecture decisions
- Code quality and best practices
- Test coverage and quality
- Documentation completeness
- Breaking changes and backward compatibility
- Security considerations
- Performance implications

Pull Request: {target}

{custom_prompt}

Please provide detailed review feedback suitable for a pull request review.""",

    "general": """You are an expert code reviewer. Please conduct a general code review of the codebase.

Focus on:
- Overall code architecture and design
- Code quality and maintainability
- Security best practices
- Performance optimization opportunities
- Technical debt identification
- Documentation quality

{custom_prompt}

Please provide a comprehensive review with prioritized recommendations."""
}


@mcp.tool()
async def codex_execute(prompt: str, work_dir: str, ctx: Context) -> str:
    """
    Execute prompt using codex for general purpose.

    Args:
        prompt (str): The prompt for codex
        work_dir (str): The working directory, e.g. /Users/kevin/Projects/demo_project
        ctx (Context): MCP context for logging
    """
    cmd = [
        "codex", "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--cd", work_dir,
        prompt,
    ]
    
    try:
        blocks = run_and_extract_codex_blocks(cmd, safe_mode=SAFE_MODE)
        # Defensive check for empty blocks
        if not blocks:
            return "Error: No codex output blocks found"
        return blocks[-1]["raw"]
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except subprocess.CalledProcessError as e:
        # Include output for better debugging
        output = e.output if hasattr(e, 'output') else (e.stderr or "")
        return f"Error executing codex command: {e}\nOutput: {output}"
    except IndexError as e:
        return "Error: No codex output blocks found (list index out of range)"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def codex_review(review_type: str, work_dir: str, target: str = "", prompt: str = "", ctx: Context = None) -> str:
    """
    Execute code review using codex with pre-defined review prompts for different scenarios.
    
    This tool provides specialized code review capabilities for various development scenarios,
    combining pre-defined review templates with custom instructions.

    Args:
        review_type (str): Type of code review to perform. Must be one of:
            - "files": Review specific files for code quality, bugs, and best practices
                       Target: comma-separated file paths (e.g., "src/main.py,src/utils.py")
                       Example: review_type="files", target="src/auth.py,src/db.py"
            
            - "staged": Review staged changes (git diff --cached) ready for commit
                       Target: not needed (automatically detects staged changes)
                       Example: review_type="staged"
            
            - "unstaged": Review unstaged changes (git diff) in working directory
                         Target: not needed (automatically detects unstaged changes)
                         Example: review_type="unstaged"
            
            - "changes": Review specific commit range or git changes
                        Target: git commit range (e.g., "HEAD~3..HEAD", "main..feature-branch")
                        Example: review_type="changes", target="HEAD~2..HEAD"
            
            - "pr": Review pull request changes comprehensively
                   Target: pull request number or identifier
                   Example: review_type="pr", target="123"
            
            - "general": General codebase review for architecture and quality
                        Target: optional, can specify scope or leave empty for full codebase
                        Example: review_type="general", target="src/"

        work_dir (str): The working directory path (e.g., "/Users/kevin/Projects/demo_project")
        
        target (str, optional): Target specification based on review_type:
            - For "files": comma-separated file paths
            - For "staged"/"unstaged": not needed (leave empty)
            - For "changes": git commit range (commit1..commit2)
            - For "pr": pull request number/identifier
            - For "general": optional scope (directory path or leave empty)
        
        prompt (str, optional): Additional custom instructions to append to the review prompt.
                               Use this to specify particular aspects to focus on or additional context.
                               Example: "Focus on security vulnerabilities and performance"
        
        ctx (Context, optional): MCP context for logging

    Returns:
        str: Detailed code review results from codex

    Examples:
        # Review specific files with security focus
        codex_review("files", "/path/to/project", "src/auth.py,src/api.py", "Focus on security vulnerabilities")
        
        # Review staged changes before commit
        codex_review("staged", "/path/to/project")
        
        # Review unstaged work-in-progress changes
        codex_review("unstaged", "/path/to/project", "", "Check for incomplete implementations")
        
        # Review recent commits
        codex_review("changes", "/path/to/project", "HEAD~3..HEAD", "Look for performance regressions")
        
        # Review pull request
        codex_review("pr", "/path/to/project", "456", "Focus on test coverage")
        
        # General codebase review
        codex_review("general", "/path/to/project", "src/", "Identify technical debt")
    """
    if review_type not in REVIEW_PROMPTS:
        raise ValueError(f"Invalid review_type '{review_type}'. Must be one of: {list(REVIEW_PROMPTS.keys())}")
    
    # Get the appropriate review prompt template
    template = REVIEW_PROMPTS[review_type]
    
    # Format the template with target and custom prompt
    custom_prompt_section = f"Additional instructions: {prompt}" if prompt else ""
    final_prompt = template.format(
        target=target if target else "current scope",
        custom_prompt=f"\n{custom_prompt_section}" if custom_prompt_section else ""
    )
    
    cmd = [
        "codex", "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--cd", work_dir,
        final_prompt,
    ]
    
    try:
        blocks = run_and_extract_codex_blocks(cmd, safe_mode=SAFE_MODE)
        # Defensive check for empty blocks
        if not blocks:
            return "Error: No codex output blocks found"
        return blocks[-1]["raw"]
    except FileNotFoundError as e:
        return f"Error: {str(e)}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except subprocess.CalledProcessError as e:
        # Include output for better debugging
        output = e.output if hasattr(e, 'output') else (e.stderr or "")
        return f"Error executing codex command: {e}\nOutput: {output}"
    except IndexError as e:
        return "Error: No codex output blocks found (list index out of range)"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def main():
    """Entry point for the MCP server"""
    global SAFE_MODE
    
    parser = argparse.ArgumentParser(
        prog="codex-as-mcp",
        description="MCP server that provides codex agent tools"
    )
    parser.add_argument(
        "--yolo", 
        action="store_true",
        help="Enable writable mode (allows file modifications, git operations, etc.)"
    )
    parser.add_argument(
        "--help-modes",
        action="store_true", 
        help="Show detailed explanation of safe vs writable modes"
    )
    
    args = parser.parse_args()
    
    if args.help_modes:
        print("""
Codex-as-MCP Execution Modes:

[SAFE] Safe Mode (default):
  - Read-only operations only
  - No file modifications
  - No git operations  
  - Safe for exploration and analysis
  
[WRITABLE] Writable Mode (--yolo):
  - Full codex agent capabilities
  - Can modify files, run git commands
  - Sequential execution prevents conflicts
  - Use with caution in production
  
Why Sequential Execution?
Codex is an agent that modifies files and system state. Running multiple
instances in parallel could cause file conflicts, git race conditions,
and conflicting system modifications. Sequential execution is safer.
""")
        sys.exit(0)
    
    # Set safe mode based on --yolo flag
    SAFE_MODE = not args.yolo
    
    if SAFE_MODE:
        print("[SAFE] Running in SAFE mode (read-only). Use --yolo for writable mode.")
    else:
        print("[WRITABLE] Running in WRITABLE mode. Codex can modify files and system state.")
    
    mcp.run()


if __name__ == "__main__":
    main()
