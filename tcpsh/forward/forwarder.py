from __future__ import annotations

import asyncio


class Forwarder:
    def __init__(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int,
        dial_timeout: float = 10.0,
    ) -> None:
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.dial_timeout = dial_timeout
        self.bytes_tx = 0
        self.bytes_rx = 0
        self._server: asyncio.AbstractServer | None = None

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
            src: asyncio.StreamReader, dst: asyncio.StreamWriter, is_tx: bool
        ) -> None:
            try:
                while True:
                    chunk = await src.read(4096)
                    if not chunk:
                        break
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
            pipe(client_r, remote_w, is_tx=True),
            pipe(remote_r, client_w, is_tx=False),
        )

    async def close(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def stats(self) -> dict:
        return {"tx": self.bytes_tx, "rx": self.bytes_rx}
