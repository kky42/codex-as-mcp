from mcp.server.fastmcp import FastMCP, Context
import subprocess
import re
import argparse
import sys
from typing import List, Dict, Optional, Sequence

from .session_manager import SessionManager

# Global safe mode setting
SAFE_MODE = True

mcp = FastMCP("codex-as-mcp")

# 会话管理器，用于根据 session_id 维护历史
session_manager = SessionManager()

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
    # Modify command based on safe mode
    final_cmd = list(cmd)
    if safe_mode:
        # Replace --dangerously-bypass-approvals-and-sandbox with read-only mode
        if "--dangerously-bypass-approvals-and-sandbox" in final_cmd:
            idx = final_cmd.index("--dangerously-bypass-approvals-and-sandbox")
            final_cmd[idx:idx+1] = ["--sandbox", "read-only", "--ask-for-approval", "never"]
    
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
async def codex_execute(prompt: str, work_dir: str, session_id: Optional[str] = None, ctx: Context = None) -> Dict[str, str]:
    """执行通用 Codex 指令，可选地绑定到已有会话"""

    if not session_id:
        session_id = session_manager.new_session()
    history = session_manager.get(session_id)
    history_text = "\n".join(m["content"] for m in history)
    final_prompt = f"{history_text}\n{prompt}" if history_text else prompt

    cmd = [
        "codex", "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--cd", work_dir,
        final_prompt,
    ]

    try:
        blocks = run_and_extract_codex_blocks(cmd, safe_mode=SAFE_MODE)
        if not blocks:
            return {"session_id": session_id, "output": "Error: No codex output blocks found"}
        response = blocks[-1]["raw"]
        session_manager.append(session_id, "user", prompt)
        session_manager.append(session_id, "assistant", response)
        return {"session_id": session_id, "output": response}
    except ValueError as e:
        return {"session_id": session_id, "output": f"Error: {str(e)}"}
    except subprocess.CalledProcessError as e:
        output = e.output if hasattr(e, 'output') else (e.stderr or "")
        return {"session_id": session_id, "output": f"Error executing codex command: {e}\nOutput: {output}"}
    except IndexError:
        return {"session_id": session_id, "output": "Error: No codex output blocks found (list index out of range)"}
    except Exception as e:
        return {"session_id": session_id, "output": f"Unexpected error: {str(e)}"}


@mcp.tool()
async def codex_continue(session_id: str, message: str, work_dir: str, ctx: Context = None) -> Dict[str, str]:
    """在指定会话里追加消息并获取响应"""

    history = session_manager.get(session_id)
    history_text = "\n".join(m["content"] for m in history)
    final_prompt = f"{history_text}\n{message}" if history_text else message

    cmd = [
        "codex", "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--cd", work_dir,
        final_prompt,
    ]

    try:
        blocks = run_and_extract_codex_blocks(cmd, safe_mode=SAFE_MODE)
        if not blocks:
            return {"session_id": session_id, "output": "Error: No codex output blocks found"}
        response = blocks[-1]["raw"]
        session_manager.append(session_id, "user", message)
        session_manager.append(session_id, "assistant", response)
        return {"session_id": session_id, "output": response}
    except ValueError as e:
        return {"session_id": session_id, "output": f"Error: {str(e)}"}
    except subprocess.CalledProcessError as e:
        output = e.output if hasattr(e, 'output') else (e.stderr or "")
        return {"session_id": session_id, "output": f"Error executing codex command: {e}\nOutput: {output}"}
    except IndexError:
        return {"session_id": session_id, "output": "Error: No codex output blocks found (list index out of range)"}
    except Exception as e:
        return {"session_id": session_id, "output": f"Unexpected error: {str(e)}"}

@mcp.tool()
async def codex_review(
    review_type: str,
    work_dir: str,
    target: str = "",
    prompt: str = "",
    session_id: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, str]:
    """使用预定义模板进行代码审查，可选地绑定到会话"""

    if review_type not in REVIEW_PROMPTS:
        raise ValueError(
            f"Invalid review_type '{review_type}'. Must be one of: {list(REVIEW_PROMPTS.keys())}"
        )

    if not session_id:
        session_id = session_manager.new_session()
    history = session_manager.get(session_id)

    template = REVIEW_PROMPTS[review_type]
    custom_prompt_section = f"Additional instructions: {prompt}" if prompt else ""
    user_prompt = template.format(
        target=target if target else "current scope",
        custom_prompt=f"\n{custom_prompt_section}" if custom_prompt_section else "",
    )

    history_text = "\n".join(m["content"] for m in history)
    final_prompt = f"{history_text}\n{user_prompt}" if history_text else user_prompt

    cmd = [
        "codex", "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--cd", work_dir,
        final_prompt,
    ]

    try:
        blocks = run_and_extract_codex_blocks(cmd, safe_mode=SAFE_MODE)
        if not blocks:
            return {"session_id": session_id, "output": "Error: No codex output blocks found"}
        response = blocks[-1]["raw"]
        session_manager.append(session_id, "user", user_prompt)
        session_manager.append(session_id, "assistant", response)
        return {"session_id": session_id, "output": response}
    except ValueError as e:
        return {"session_id": session_id, "output": f"Error: {str(e)}"}
    except subprocess.CalledProcessError as e:
        output = e.output if hasattr(e, 'output') else (e.stderr or "")
        return {"session_id": session_id, "output": f"Error executing codex command: {e}\nOutput: {output}"}
    except IndexError:
        return {"session_id": session_id, "output": "Error: No codex output blocks found (list index out of range)"}
    except Exception as e:
        return {"session_id": session_id, "output": f"Unexpected error: {str(e)}"}


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

🔒 Safe Mode (default):
  - Read-only operations only
  - No file modifications
  - No git operations  
  - Safe for exploration and analysis
  
⚡ Writable Mode (--yolo):
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
        print("🔒 Running in SAFE mode (read-only). Use --yolo for writable mode.")
    else:
        print("⚡ Running in WRITABLE mode. Codex can modify files and system state.")
    
    mcp.run()


if __name__ == "__main__":
    main()
