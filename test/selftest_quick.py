# -*- coding: utf-8 -*-
"""
最快速自测（无子进程、无 CLI、无外部 codex）：
- 仅验证工具函数 codex_execute / codex_continue / codex_review
- 强制 3s 总超时保护
- 在系统临时目录运行，sessions.json 不写入仓库
运行：python3 -u test/selftest_quick.py
"""
import sys
import os
import asyncio
import tempfile
from pathlib import Path

# 将 stubs 与 src 放入路径前端，避免真实依赖
ROOT = Path(__file__).resolve().parents[1]
STUBS = ROOT / "test" / "stubs"
SRC = ROOT / "src"
sys.path[:0] = [str(STUBS), str(SRC)]

from codex_as_mcp import server  # noqa: E402

# 伪造执行器：成功与超时两种

def fake_run_success(cmd, **kw):
    return [{
        "timestamp": "t",
        "tag": "codex",
        "body": "ok",
        "raw": "[t] codex\nok\n",
    }]

async def main():
    # 在临时目录中执行，避免写入仓库
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        server.run_and_extract_codex_blocks = fake_run_success

        r1 = await server.codex_execute("print(1)", ".", model="gpt-5 high", timeout=0.5, session_id=None, ctx=None)
        assert r1.get("session_id"), "codex_execute 未返回 session_id"
        assert isinstance(r1.get("output"), str) and r1["output"], "codex_execute 无输出"
        sid = r1["session_id"]
        print("EXECUTE PASS", sid)

        r2 = await server.codex_continue(sid, "and then", ".", model="gpt-5 low", timeout=0.5, ctx=None)
        assert r2.get("session_id") == sid, "codex_continue 会话不一致"
        assert isinstance(r2.get("output"), str) and r2["output"], "codex_continue 无输出"
        print("CONTINUE PASS")

        r3 = await server.codex_review("staged", ".", target="", prompt="extra", model="gpt-5 medium", timeout=0.5, session_id=None, ctx=None)
        assert r3.get("session_id"), "codex_review 未返回 session_id"
        assert isinstance(r3.get("output"), str) and r3["output"], "codex_review 无输出"
        print("REVIEW PASS", r3["session_id"])

        # 非法模型提示路径
        r4 = await server.codex_execute("noop", ".", model="invalid-model", timeout=0.1, session_id=None, ctx=None)
        assert r4.get("session_id"), "invalid-model 未返回 session_id"
        print("INVALID_MODEL PASS")

        print("SESSIONS PATH", Path(d, "sessions.json").exists())
        print("ALL PASS")

if __name__ == "__main__":
    try:
        asyncio.run(asyncio.wait_for(main(), timeout=3.0))
    except asyncio.TimeoutError:
        print("TIMEOUT 3s")
        sys.exit(124)
