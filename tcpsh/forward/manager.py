from __future__ import annotations

from dataclasses import dataclass
from .forwarder import Forwarder
from .proxy import Proxy


@dataclass
class Entry:
    kind: str  # 'fwd' | 'proxy'
    instance: Forwarder | Proxy
    remote: str
    log_file: str | None = None


class ForwardManager:
    def __init__(self) -> None:
        self._entries: dict[int, Entry] = {}

    async def open_forward(
        self, local_port: int, remote_host: str, remote_port: int, dial_timeout: float
    ) -> None:
        if local_port in self._entries:
            raise ValueError(f"Port {local_port} already in use")
        fwd = Forwarder(local_port, remote_host, remote_port, dial_timeout)
        await fwd.start()
        self._entries[local_port] = Entry(
            kind="fwd", instance=fwd, remote=f"{remote_host}:{remote_port}"
        )

    async def open_proxy(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int,
        log_file: str | None,
        dial_timeout: float,
    ) -> None:
        if local_port in self._entries:
            raise ValueError(f"Port {local_port} already in use")
        proxy = Proxy(local_port, remote_host, remote_port, log_file, dial_timeout)
        await proxy.start()
        self._entries[local_port] = Entry(
            kind="proxy",
            instance=proxy,
            remote=f"{remote_host}:{remote_port}",
            log_file=log_file,
        )

    async def close(self, local_port: int) -> None:
        entry = self._entries.pop(local_port, None)
        if entry is None:
            raise ValueError(f"No forward on port {local_port}")
        await entry.instance.close()

    def set_proxy_log(self, local_port: int, path: str) -> None:
        entry = self._entries.get(local_port)
        if not entry or entry.kind != "proxy":
            raise ValueError(f"No proxy on port {local_port}")
        entry.instance.set_log_file(path)  # type: ignore[union-attr]
        entry.log_file = path

    def list(self) -> list[dict]:
        result = []
        for lport, e in self._entries.items():
            result.append(
                {
                    "local_port": lport,
                    "type": e.kind,
                    "remote": e.remote,
                    "stats": e.instance.stats(),
                    "log_file": e.log_file,
                }
            )
        return result

    async def close_all(self) -> None:
        for lport in list(self._entries):
            await self.close(lport)
