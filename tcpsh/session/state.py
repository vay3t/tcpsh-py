from __future__ import annotations

from enum import Enum, auto


class State(str, Enum):
    ACTIVE = "active"
    FOREGROUND = "foreground"
    BACKGROUND = "background"
    DEAD = "dead"
