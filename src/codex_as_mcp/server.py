from mcp.server.fastmcp import FastMCP, Context
import subprocess
import re
import argparse
import sys
from typing import List, Dict, Optional, Sequence
from pathlib import Path
import yaml

# Global safe mode setting
SAFE_MODE = True
DEFAULT_TIMEOUT = 300.0

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
    safe_mode: bool = True,
    timeout: Optional[float] = None,
) -> List[Dict[str, str]]:
    """
    运行命令并抽取日志块。每个块由形如
    [YYYY-MM-DDTHH:MM:SS] <tag>
    <正文...直到下一个时间戳头或文件结束>
    组成。

    :param cmd: 完整命令（列表形式）
    :param tags: 需要过滤的 tag 列表（大小写不敏感）。None 表示不过滤。
    :param last_n: 返回最后 N 个匹配块
    :param safe_mode: 是否启用安全模式
    :param timeout: 子进程超时时间（秒）
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
        final_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
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


# Default review prompts for different scenarios
DEFAULT_REVIEW_PROMPTS = {
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


def load_review_prompts() -> Dict[str, str]:
    """Load review prompts from project root YAML file.

    Returns:
        dict: Review prompt templates.
    """
    config_path = Path(__file__).resolve().parents[2] / "review_prompts.yaml"
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return DEFAULT_REVIEW_PROMPTS


# Loaded review prompts
REVIEW_PROMPTS = load_review_prompts()

# Temporary gpt-5 model options
ALLOWED_MODELS = {
    "gpt-5 minimal": "fastest responses with limited reasoning; ideal for coding, instructions, or lightweight tasks",
    "gpt-5 low": "balances speed with some reasoning; useful for straightforward queries and short explanations",
    "gpt-5 medium": "default setting; provides a solid balance of reasoning depth and latency for general-purpose tasks",
    "gpt-5 high": "maximizes reasoning depth for complex or ambiguous problems",
}


@mcp.tool()
async def codex_execute(prompt: str, work_dir: str, model: str = "", timeout: Optional[float] = None, ctx: Context = None) -> str:
    """
    通用 Codex 执行工具，支持指定模型与超时。

    参数:
        - prompt (str): Codex 提示词
        - work_dir (str): 工作目录（例如 /Users/kevin/Projects/demo_project）
        - model (str, 可选): 指定 Codex 模型；未提供或不在允许列表则使用默认模型
        - timeout (float, 可选): codex 命令超时时间（秒）
        - ctx (Context, 可选): MCP 上下文（用于日志输出）

    示例:
        codex_execute("print('hello')", "/path/to/project", model="gpt-5 high", timeout=120)
    """
    cmd = [
        "codex", "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--cd", work_dir,
    ]
    if model:
        if model in ALLOWED_MODELS:
            cmd.extend(["--model", model])
        else:
            warn = (
                f"模型 '{model}' 暂不支持，将使用 Codex 默认模型。\n当前可选模型：\n"
                + "\n".join(f"- {m} — {desc}" for m, desc in ALLOWED_MODELS.items())
            )
            if ctx:
                ctx.console.print(warn)
            else:
                print(warn)
    cmd.append(prompt)
    
    try:
        blocks = run_and_extract_codex_blocks(cmd, safe_mode=SAFE_MODE, timeout=timeout)
        # Defensive check for empty blocks
        if not blocks:
            return "Error: No codex output blocks found"
        return blocks[-1]["raw"]
    except ValueError as e:
        return f"Error: {str(e)}"
    except subprocess.CalledProcessError as e:
        # Include output for better debugging
        output = e.output if hasattr(e, 'output') else (e.stderr or "")
        return f"Error executing codex command: {e}\nOutput: {output}"
    except subprocess.TimeoutExpired as e:
        return f"Error: Command timed out after {e.timeout} seconds"
    except IndexError as e:
        return "Error: No codex output blocks found (list index out of range)"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def codex_review(
    review_type: str,
    work_dir: str,
    target: str = "",
    prompt: str = "",
    model: str = "",
    timeout: Optional[float] = None,
    ctx: Context = None,
) -> str:
    """
    基于预设模板执行 Codex 代码审查，支持指定模型与超时。

    该工具针对多种开发场景提供专业化的代码审查能力，
    将预设的审查模板与自定义说明组合使用以获得更高质量的审查结果。

    参数:
        - review_type (str): 审查类型，必须是以下之一：
            - "files": 审查指定文件的代码质量、缺陷与最佳实践
                         目标：逗号分隔的文件路径（例如 "src/main.py,src/utils.py"）
            - "staged": 审查已暂存更改（git diff --cached），评估是否可提交
                         目标：不需要（自动检测）
            - "unstaged": 审查未暂存更改（git diff），发现未完成实现等问题
                         目标：不需要（自动检测）
            - "changes": 审查指定提交范围的变更
                         目标：Git 提交范围（例如 "HEAD~3..HEAD"）
            - "pr": 审查指定拉取请求的整体变更
                         目标：PR 编号或标识（例如 "123"）
            - "general": 通用代码库审查（架构与质量）
                         目标：可选的目录范围，或留空以覆盖全仓库

        - work_dir (str): 工作目录路径（例如 "/Users/kevin/Projects/demo_project"）
        - target (str, 可选): 随审查类型变化的目标参数；见上述说明
        - prompt (str, 可选): 追加到审查模板的自定义说明（关注点/上下文）
        - model (str, 可选): 指定 Codex 模型；未提供或不在允许列表则使用默认模型
        - timeout (float, 可选): codex 命令超时时间（秒）
        - ctx (Context, 可选): MCP 上下文（用于日志输出）

    返回:
        - str: 来自 Codex 的详细代码审查结果

    示例:
        # 审查指定文件并关注安全问题
        codex_review("files", "/path/to/project", "src/auth.py,src/api.py", "关注安全漏洞", model="gpt-5 high")

        # 提交前审查已暂存更改
        codex_review("staged", "/path/to/project", model="gpt-5 low")

        # 审查最近提交范围
        codex_review("changes", "/path/to/project", "HEAD~3..HEAD", "关注性能回退")
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
        "--dangerously-bypass-approvals-and-sandbox",
        "--cd", work_dir,
    ]
    if model:
        if model in ALLOWED_MODELS:
            cmd.extend(["--model", model])
        else:
            warn = (
                f"模型 '{model}' 暂不支持，将使用 Codex 默认模型。\n当前可选模型：\n"
                + "\n".join(f"- {m} — {desc}" for m, desc in ALLOWED_MODELS.items())
            )
            if ctx:
                ctx.console.print(warn)
            else:
                print(warn)
    cmd.append(final_prompt)
    
    try:
        blocks = run_and_extract_codex_blocks(cmd, safe_mode=SAFE_MODE, timeout=timeout)
        # Defensive check for empty blocks
        if not blocks:
            return "Error: No codex output blocks found"
        return blocks[-1]["raw"]
    except ValueError as e:
        return f"Error: {str(e)}"
    except subprocess.CalledProcessError as e:
        # Include output for better debugging
        output = e.output if hasattr(e, 'output') else (e.stderr or "")
        return f"Error executing codex command: {e}\nOutput: {output}"
    except subprocess.TimeoutExpired as e:
        return f"Error: Command timed out after {e.timeout} seconds"
    except IndexError as e:
        return "Error: No codex output blocks found (list index out of range)"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def main():
    """Entry point for the MCP server"""
    global SAFE_MODE, DEFAULT_TIMEOUT
    
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
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Timeout in seconds for codex commands"
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
    
    # Set safe mode and timeout based on CLI args
    SAFE_MODE = not args.yolo
    DEFAULT_TIMEOUT = args.timeout

    if SAFE_MODE:
        print("🔒 Running in SAFE mode (read-only). Use --yolo for writable mode.")
    else:
        print("⚡ Running in WRITABLE mode. Codex can modify files and system state.")
    
    mcp.run()


if __name__ == "__main__":
    main()
