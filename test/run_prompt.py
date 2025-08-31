# -*- coding: utf-8 -*-
"""
一次性运行：不启动服务器、不依赖外部 codex/mcp。
- 在临时目录执行，sessions.json 不写入仓库
- 使用本地 stub 拦截外部执行
运行：python3 -u test/run_prompt.py
"""
import sys
import os
import asyncio
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUBS = ROOT / "test" / "stubs"
SRC = ROOT / "src"
sys.path[:0] = [str(STUBS), str(SRC)]

from codex_as_mcp import server  # noqa: E402


def fake_run(cmd, **kw):
    # 将最后一个参数视为 prompt，构造一个伪输出块
    prompt = cmd[-1] if cmd else ""
    body = f"任务已执行：{prompt}\n结果：ok"
    return [{
        "timestamp": "t",
        "tag": "codex",
        "body": body,
        "raw": f"[t] codex\n{body}\n",
    }]


async def main():
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        server.run_and_extract_codex_blocks = fake_run
        r = await server.codex_execute(
            "请用 Python 打印 Hello, MCP",
            ".",
            model="gpt-5 medium",
            timeout=0.5,
            session_id=None,
            ctx=None,
        )
        print("SESSION", r.get("session_id"))
        print("OUTPUT\n" + (r.get("output", "").strip()))


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=3.0))
