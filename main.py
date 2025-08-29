import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

CONFIG_PATH = Path.home() / ".codex" / "mcp.json"
CONFIG_FILE = "env.config.json"
VENV_DIR = ".venv"

def connect_to_mcp(address: str) -> None:
    """尝试连接到指定地址的 MCP 服务器（示例实现）。"""
    print(f"已连接 MCP 服务器：{address}")

def ensure_mcp_server() -> None:
    """确保 MCP 服务器已运行：若存在配置则连接，否则尝试启动。"""
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            addr = data.get("address") or data.get("url")
            if addr:
                connect_to_mcp(addr)
                return
        except json.JSONDecodeError:
            pass
    print("未检测到 MCP 服务器，尝试启动...")
    for cmd in (["uv", "run", "codex_mcp.server"], ["npm", "run", "mcp-server"]):
        try:
            subprocess.Popen(cmd)
            print(f"已启动 MCP 服务器：{' '.join(cmd)}")
            return
        except FileNotFoundError:
            continue
    print("无法启动 MCP 服务器，请检查环境。")

def parse_args(argv: Optional[Sequence[str]] = None):
    """解析命令行参数：支持 --mcp 开关与 run 子命令的透传参数。"""
    parser = argparse.ArgumentParser(prog="codex")
    parser.add_argument("--mcp", dest="mcp", action="store_true", help="启用 MCP 集成")
    parser.add_argument("--no-mcp", dest="mcp", action="store_false", help="禁用 MCP 集成")
    parser.set_defaults(mcp=False)
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="运行 codex")
    run_parser.add_argument("extra", nargs=argparse.REMAINDER, help="传递给 codex 的额外参数")
    return parser.parse_args(argv), parser

def ensure_env():
    config_path = pathlib.Path(CONFIG_FILE)
    if config_path.exists():
        with config_path.open() as f:
            data = json.load(f)
        python_cmd = data.get("python", "python3")
        python_path = data.get("python_path")
        venv_dir = data.get("venv_path", VENV_DIR)
        deps = data.get("dependencies", {})
        venv_python = pathlib.Path(venv_dir) / ("Scripts" if os.name == "nt" else "bin") / "python"
        if pathlib.Path(sys.executable).resolve() != venv_python.resolve():
            if not venv_python.exists():
                if python_path:
                    python_exe = python_path
                else:
                    python_exe = shutil.which(python_cmd) or sys.executable
                subprocess.check_call([str(python_exe), "-m", "venv", venv_dir])
            os.execv(str(venv_python), [str(venv_python), *sys.argv])
        if deps:
            subprocess.check_call([str(venv_python), "-m", "ensurepip", "--upgrade"])
            packages = [f"{name}=={ver}" for name, ver in deps.items()]
            subprocess.check_call([str(venv_python), "-m", "pip", "install", *packages])
    else:
        lock_file = pathlib.Path("uv.lock")
        if lock_file.exists():
            try:
                subprocess.check_call(["uv", "pip", "install", "-r", str(lock_file)])
            except FileNotFoundError:
                print("未找到 uv 命令，无法根据 uv.lock 安装依赖", file=sys.stderr)

def main(argv: Optional[Sequence[str]] = None) -> None:
    ensure_env()
    args, parser = parse_args(argv)
    if args.mcp:
        ensure_mcp_server()
    if args.command == "run":
        cmd = ["codex", "run"] + args.extra
        try:
            subprocess.run(cmd, check=False)
        except FileNotFoundError:
            print("未找到 codex CLI，请先安装。")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

