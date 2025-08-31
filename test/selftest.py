# -*- coding: utf-8 -*-
"""
零依赖、零仓库写入的自测脚本：
- 在 test/stubs 下提供最小 mcp 与 yaml stub，避免安装依赖
- 将 test/stubs 与 src 加入 sys.path
- 运行 codex_as_mcp 的 --help-modes 与标志位测试
- monkeypatch run_and_extract_codex_blocks，异步验证 codex_execute/codex_continue/codex_review
- 会话文件 sessions.json 仅写入临时目录
"""
import os
import sys
import runpy
import asyncio
import tempfile
import subprocess
from pathlib import Path

# 将 stubs 与 src 放入路径前端
ROOT = Path(__file__).resolve().parents[1]
STUBS = ROOT / "test" / "stubs"
SRC = ROOT / "src"
for p in (STUBS, SRC):
    sys.path.insert(0, str(p))

print("[selftest] sys.version:", sys.version)
print("[selftest] sys.path[0:3]:", sys.path[0:3])

# 预加载并打补丁，确保 main() 不会真正阻塞在 mcp.run()
import importlib
_server_mod = importlib.import_module("codex_as_mcp.server")
def _stub_mcp_run():
    print("[selftest] stub mcp.run() called")
    return None
_server_mod.mcp.run = _stub_mcp_run

def run_cli_with_timeout(argv, timeout_sec: float, label: str):
    """在独立子进程中运行 codex_as_mcp（带 stub）并设置超时，避免主进程卡死。"""
    env = os.environ.copy()
    # 确保子进程同样可以找到 stubs 与 src
    env["PYTHONPATH"] = os.pathsep.join([str(STUBS), str(SRC), env.get("PYTHONPATH", "")])
    code = (
        "import sys, runpy, importlib; "
        f"sys.argv={argv!r}; "
        "m=importlib.import_module('codex_as_mcp.server'); "
        "def _stub(): print('[selftest-sub] stub mcp.run() called'); return None; "
        "m.mcp.run=_stub; "
        "runpy.run_module('codex_as_mcp.__main__', run_name='__main__')"
    )
    print(f"[selftest] {label}: start (timeout={timeout_sec}s)")
    try:
        cp = subprocess.run([sys.executable, "-u", "-c", code], capture_output=True, text=True, timeout=timeout_sec, env=env)
        print(f"[selftest] {label}: rc={cp.returncode}")
        if cp.stdout:
            print(f"[selftest] {label} stdout:\n{cp.stdout}")
        if cp.stderr:
            print(f"[selftest] {label} stderr:\n{cp.stderr}")
    except subprocess.TimeoutExpired as e:
        print(f"[selftest] {label}: TIMEOUT after {timeout_sec}s")
    except Exception as e:
        print(f"[selftest] {label}: ERROR {e}")

# 1) CLI: --help-modes（子进程 + 超时）
print("\n=== STEP 1: help-modes ===")
run_cli_with_timeout(["codex_as_mcp", "--help-modes"], timeout_sec=10.0, label="help-modes")

# 2) CLI: flags --yolo/--auto-approve/--timeout
print("\n=== STEP 2: flags ===")
run_cli_with_timeout(["codex_as_mcp", "--yolo", "--auto-approve", "--timeout", "1.2"], timeout_sec=10.0, label="flags")

# 3) 工具函数：模拟执行与超时
print("\n=== STEP 3: tools ===")
from codex_as_mcp import server  # noqa: E402

# 保留原函数以便需要时还原
_original_run = server.run_and_extract_codex_blocks

def fake_run_success(cmd, **kw):
    # 模拟一次成功输出
    return [{
        "timestamp": "2025-08-29T11:40:00",
        "tag": "codex",
        "body": "ok",
        "raw": "[2025-08-29T11:40:00] codex\nok\n",
    }]

def fake_run_timeout(cmd, **kw):
    # 模拟子进程超时
    raise subprocess.TimeoutExpired(cmd=cmd, timeout=kw.get("timeout") or 0.1)

# 在临时目录下运行，避免写入仓库
with tempfile.TemporaryDirectory() as d:
    os.chdir(d)
    print("[selftest] workdir:", d)

    async def main():
        # 3.1 首次执行：成功路径 + 新会话
        server.run_and_extract_codex_blocks = fake_run_success
        r1 = await server.codex_execute("print(1)", ".", model="gpt-5 high", timeout=1.0, session_id=None, ctx=None)
        assert r1.get("session_id"), "codex_execute 未返回 session_id"
        assert isinstance(r1.get("output"), str) and r1["output"], "codex_execute 无输出"
        sid = r1["session_id"]
        print("[selftest] EXECUTE: ok, sid=", sid)

        # 3.2 继续会话：成功路径
        r2 = await server.codex_continue(sid, "and then", ".", model="gpt-5 low", timeout=2.0, ctx=None)
        assert r2.get("session_id") == sid, "codex_continue 会话不一致"
        assert isinstance(r2.get("output"), str) and r2["output"], "codex_continue 无输出"
        print("[selftest] CONTINUE: ok")

        # 3.3 审查工具：成功路径 + 新会话
        r3 = await server.codex_review("staged", ".", target="", prompt="extra", model="gpt-5 medium", timeout=3.0, session_id=None, ctx=None)
        assert r3.get("session_id"), "codex_review 未返回 session_id"
        assert isinstance(r3.get("output"), str) and r3["output"], "codex_review 无输出"
        print("[selftest] REVIEW: ok, sid=", r3["session_id"])

        # 3.4 非法模型：仅应提示警告，但不中断
        r4 = await server.codex_execute("noop", ".", model="invalid-model", timeout=0.5, session_id=None, ctx=None)
        assert r4.get("session_id"), "invalid-model 测试未返回 session_id"
        assert isinstance(r4.get("output"), str), "invalid-model 测试无输出字段"
        print("[selftest] INVALID_MODEL: ok")

        # 3.5 超时：应走 TimeoutExpired 分支
        server.run_and_extract_codex_blocks = fake_run_timeout
        r5 = await server.codex_execute("sleep", ".", model="gpt-5 minimal", timeout=0.1, session_id=None, ctx=None)
        assert "timed out" in r5.get("output", ""), "超时分支未生效"
        print("[selftest] TIMEOUT: ok")

    try:
        asyncio.run(asyncio.wait_for(main(), timeout=10.0))
    except asyncio.TimeoutError:
        print("[selftest] tools: TIMEOUT after 10s")

    sess_path = Path("sessions.json")
    print("[selftest] sessions.json exists:", sess_path.exists())
    if sess_path.exists():
        head = sess_path.read_text(encoding="utf-8").splitlines()[:10]
        print("[selftest] sessions.json head:")
        for line in head:
            print(line)

# 还原原函数，防止意外影响
server.run_and_extract_codex_blocks = _original_run

print("\nALL TESTS PASSED")
