# -*- coding: utf-8 -*-
"""
以“启动 CLI”的方式执行一个简单任务：
- 通过 __main__ 入口解析 CLI（--yolo/--timeout 等）
- 在调用 mcp.run() 处打桩，转而执行一次 codex_execute 并退出
- 使用本地 fake 执行器，不会调用外部 codex
- 3 秒总超时
运行：python3 -u test/run_cli_task.py
"""
import sys
import os
import asyncio
import tempfile
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUBS = ROOT / "test" / "stubs"
SRC = ROOT / "src"
sys.path[:0] = [str(STUBS), str(SRC)]

from codex_as_mcp import server  # noqa: E402


def fake_run(cmd, **kw):
    prompt = cmd[-1] if cmd else ""
    body = f"CLI-任务执行：{prompt}\n结果：ok"
    return [{
        "timestamp": "t",
        "tag": "codex",
        "body": body,
        "raw": f"[t] codex\n{body}\n",
    }]


async def main():
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        # 拦截外部执行
        server.run_and_extract_codex_blocks = fake_run

        # 将 mcp.run() 改为：在新线程中使用 asyncio.run 执行一次 codex_execute 并退出
        import threading

        def _run_once():
            result_holder = {}

            def _worker():
                r = asyncio.run(
                    server.codex_execute(
                        "请将 1+1 的结果打印出来",
                        ".",
                        model="gpt-5 medium",
                        timeout=0.5,
                        session_id=None,
                        ctx=None,
                    )
                )
                result_holder["r"] = r

            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            t.join(timeout=2.0)
            r = result_holder.get("r", {"session_id": "", "output": "(no result)"})
            print("SESSION", r.get("session_id"))
            print("OUTPUT\n" + (r.get("output", "").strip()))
            return None

        server.mcp.run = _run_once

        # 以 CLI 方式进入（参数可根据需要调整）
        sys.argv = ["codex_as_mcp", "--timeout", "2.0"]
        runpy.run_module("codex_as_mcp.__main__", run_name="__main__")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=3.0))
