from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TOOL_VERBS = frozenset(
    [
        "open",
        "close",
        "kill",
        "use",
        "list",
        "fwd",
        "proxy",
        "info",
        "help",
        "clear",
        "exit",
    ]
)

CmdKind = Literal["tool", "system", "special", "passthrough", "empty"]


@dataclass
class Cmd:
    kind: CmdKind
    verb: str = ""
    args: list[str] = None  # type: ignore[assignment]
    raw: str = ""

    def __post_init__(self) -> None:
        if self.args is None:
            self.args = []


def parse(line: str, session_mode: bool = False) -> Cmd:
    trimmed = line.strip()
    if not trimmed:
        return Cmd(kind="empty")

    if trimmed.startswith("+"):
        return Cmd(kind="special", verb=trimmed[1:].lower(), raw=trimmed)

    if trimmed.startswith("!"):
        return Cmd(kind="system", raw=trimmed[1:])

    parts = trimmed.split()
    verb = parts[0].lower()
    args = parts[1:]

    if not session_mode and verb in TOOL_VERBS:
        return Cmd(kind="tool", verb=verb, args=args, raw=trimmed)

    if session_mode:
        if verb in TOOL_VERBS:
            return Cmd(kind="tool", verb=verb, args=args, raw=trimmed)
        return Cmd(kind="passthrough", raw=trimmed)

    return Cmd(kind="tool", verb=verb, args=args, raw=trimmed)


def parse_port_idx(s: str) -> tuple[int, int] | None:
    parts = s.split(":")
    try:
        port = int(parts[0])
        idx = int(parts[1]) if len(parts) > 1 else 1
        return port, idx
    except (ValueError, IndexError):
        return None


def parse_remote(s: str) -> tuple[str, int] | None:
    pos = s.rfind(":")
    if pos < 0:
        return None
    host = s[:pos]
    try:
        port = int(s[pos + 1 :])
    except ValueError:
        return None
    if not host:
        return None
    return host, port
