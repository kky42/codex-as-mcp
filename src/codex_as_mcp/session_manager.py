import json
import os
import uuid
from typing import List, Dict


class SessionManager:
    """使用 JSON 文件持久化的简单会话管理器"""

    def __init__(self, path: str = "sessions.json") -> None:
        self.path = path
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.sessions = json.load(f)
            except Exception:
                self.sessions = {}

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.sessions, f, ensure_ascii=False, indent=2)

    def new_session(self) -> str:
        session_id = uuid.uuid4().hex
        self.sessions[session_id] = []
        self._save()
        return session_id

    def append(self, session_id: str, role: str, content: str) -> None:
        self.sessions.setdefault(session_id, []).append({"role": role, "content": content})
        self._save()

    def get(self, session_id: str) -> List[Dict[str, str]]:
        return self.sessions.get(session_id, [])
