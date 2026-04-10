from __future__ import annotations

import asyncio
from typing import Callable, Awaitable

from ..session.session import Session
from ..session.state import State


class Listener:
    def __init__(
        self,
        port: int,
        host: str = "0.0.0.0",
        on_event: Callable[[str, object], Awaitable[None]] | None = None,
    ) -> None:
        self.port = port
        self.host = host
        self._server: asyncio.AbstractServer | None = None
        self._on_event = on_event

    async def _emit(self, event: str, payload: object) -> None:
        if self._on_event:
            await self._on_event(event, payload)

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        sess = Session(reader, writer, self.port)
        await self._emit("connection", sess)

        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                sess.bytes_rx += len(chunk)
                await self._emit("data", (sess, chunk))
        except (ConnectionResetError, asyncio.IncompleteReadError, OSError):
            pass
        finally:
            sess.state = State.DEAD
            await self._emit("session_close", sess)

    async def close(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
