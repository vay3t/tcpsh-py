from __future__ import annotations

import threading
from typing import Callable

from .session import Session
from .state import State


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[int, Session] = {}
        self._lock = threading.RLock()

    def add(self, session: Session) -> None:
        with self._lock:
            self._sessions[session.id] = session

    def get(self, session_id: int) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def by_port(self, port: int) -> list[Session]:
        with self._lock:
            return [
                s
                for s in self._sessions.values()
                if s.port == port and s.state is not State.DEAD
            ]

    def all(self) -> list[Session]:
        with self._lock:
            return [s for s in self._sessions.values() if s.state is not State.DEAD]

    def remove(self, session_id: int) -> None:
        with self._lock:
            s = self._sessions.pop(session_id, None)
            if s:
                s.state = State.DEAD

    def close_all(self) -> None:
        with self._lock:
            for s in list(self._sessions.values()):
                s.force_close()
            self._sessions.clear()
