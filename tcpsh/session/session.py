from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .state import State

_id_counter = 0


def _next_id() -> int:
    global _id_counter
    _id_counter += 1
    return _id_counter


class Session:
    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int
    ) -> None:
        self.id = _next_id()
        self.port = port
        self.reader = reader
        self.writer = writer
        peer = writer.get_extra_info("peername")
        self.remote = f"{peer[0]}:{peer[1]}" if peer else "unknown"
        self.state = State.ACTIVE
        self.bytes_tx = 0
        self.bytes_rx = 0
        self.created_at = datetime.now(tz=timezone.utc)

    async def write(self, data: bytes | str) -> None:
        if self.state is State.DEAD:
            return
        if isinstance(data, str):
            data = data.encode()
        self.writer.write(data)
        await self.writer.drain()
        self.bytes_tx += len(data)

    def close(self) -> None:
        self.state = State.DEAD
        try:
            self.writer.close()
        except Exception:
            pass

    def force_close(self) -> None:
        self.close()
