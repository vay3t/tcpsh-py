from __future__ import annotations

from typing import Callable, Awaitable

from .listener import Listener


class ListenerManager:
    def __init__(self) -> None:
        self._listeners: dict[int, Listener] = {}
        self._on_event: Callable | None = None

    def on_event(self, handler: Callable) -> None:
        self._on_event = handler

    async def open(self, port: int, host: str = "0.0.0.0") -> Listener:
        if port in self._listeners:
            raise ValueError(f"Port {port} is already open")
        listener = Listener(port, host, on_event=self._on_event)
        await listener.start()
        self._listeners[port] = listener
        return listener

    async def close(self, port: int) -> None:
        listener = self._listeners.pop(port, None)
        if listener is None:
            raise ValueError(f"Port {port} is not open")
        await listener.close()

    def open_ports(self) -> list[int]:
        return list(self._listeners.keys())

    def get_listener(self, port: int) -> Listener | None:
        return self._listeners.get(port)

    async def close_all(self) -> None:
        for port in list(self._listeners):
            await self.close(port)
