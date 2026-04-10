from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path


class Proxy:
    def __init__(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int,
        log_file: str | None = None,
        dial_timeout: float = 10.0,
    ) -> None:
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.dial_timeout = dial_timeout
        self.bytes_tx = 0
        self.bytes_rx = 0
        self._log_lock = threading.Lock()
        self._log_file: Path | None = Path(log_file) if log_file else None
        self._server: asyncio.AbstractServer | None = None

    def _log(self, tag: str, data: bytes) -> None:
        if not self._log_file:
            return
        ts = datetime.now(tz=timezone.utc).isoformat()
        hex_ = data.hex()
        line = f"[{ts}] [{tag}] {hex_}\n"
        with self._log_lock:
            with self._log_file.open("a") as f:
                f.write(line)

    def set_log_file(self, path: str) -> None:
        with self._log_lock:
            self._log_file = Path(path)

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle, "0.0.0.0", self.local_port
        )

    async def _handle(
        self, client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter
    ) -> None:
        try:
            remote_r, remote_w = await asyncio.wait_for(
                asyncio.open_connection(self.remote_host, self.remote_port),
                timeout=self.dial_timeout,
            )
        except (asyncio.TimeoutError, OSError):
            client_w.close()
            return

        async def pipe(
            src: asyncio.StreamReader, dst: asyncio.StreamWriter, tag: str, is_tx: bool
        ) -> None:
            try:
                while True:
                    chunk = await src.read(4096)
                    if not chunk:
                        break
                    self._log(tag, chunk)
                    dst.write(chunk)
                    await dst.drain()
                    if is_tx:
                        self.bytes_tx += len(chunk)
                    else:
                        self.bytes_rx += len(chunk)
            except OSError:
                pass
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        await asyncio.gather(
            pipe(client_r, remote_w, "TX", is_tx=True),
            pipe(remote_r, client_w, "RX", is_tx=False),
        )

    async def close(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def stats(self) -> dict:
        return {"tx": self.bytes_tx, "rx": self.bytes_rx}
