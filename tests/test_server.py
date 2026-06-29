import asyncio
from pathlib import Path
from types import SimpleNamespace

from codex_as_mcp import server


class DummyContext:
    async def report_progress(self, *args, **kwargs):
        return None


class FakeStdin:
    def __init__(self):
        self.data = b""
        self.closed = False

    def write(self, data):
        self.data += data

    async def drain(self):
        return None

    def close(self):
        self.closed = True


class FakeStream:
    def __init__(self, data=b""):
        self.data = data

    async def read(self):
        return self.data


def test_spawn_agent_sends_prompt_via_stdin_and_uses_dash(monkeypatch):
    captured = {}
    fake_stdin = FakeStdin()

    class FakeProcess:
        stdin = fake_stdin
        stdout = FakeStream(b"codex stdout")
        stderr = FakeStream(b"")

        async def wait(self):
            output_path = Path(captured["cmd"][captured["cmd"].index("--output-last-message") + 1])
            output_path.write_text("final response", encoding="utf-8")
            return 0

        def kill(self):
            captured["killed"] = True

    async def fake_create_subprocess_exec(*cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(server, "_resolve_codex_executable", lambda: "codex")
    monkeypatch.setattr(server.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    prompt = 'hello "windows" 中文\n' * 100
    result = asyncio.run(server.spawn_agent(DummyContext(), prompt))

    assert result == "final response"
    assert captured["cmd"][-1] == "-"
    assert prompt not in captured["cmd"]
    assert captured["kwargs"]["stdin"] == server.asyncio.subprocess.PIPE
    assert fake_stdin.data == prompt.encode("utf-8")
    assert fake_stdin.closed is True


def test_spawn_agent_reports_stdin_write_failure(monkeypatch):
    class BrokenStdin:
        def write(self, data):
            raise BrokenPipeError("closed")

        async def drain(self):
            return None

        def close(self):
            return None

    proc = SimpleNamespace(
        stdin=BrokenStdin(),
        stdout=FakeStream(),
        stderr=FakeStream(),
        killed=False,
    )

    def kill():
        proc.killed = True

    proc.kill = kill

    async def fake_create_subprocess_exec(*cmd, **kwargs):
        return proc

    monkeypatch.setattr(server, "_resolve_codex_executable", lambda: "codex")
    monkeypatch.setattr(server.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    result = asyncio.run(server.spawn_agent(DummyContext(), "hello"))

    assert result.startswith("Error: Failed to send prompt to Codex agent:")
    assert proc.killed is True
