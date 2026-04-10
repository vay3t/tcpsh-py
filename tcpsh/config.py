from __future__ import annotations

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    prompt: str = "tcpsh> "
    history_file: str = str(Path.home() / ".tcpsh_history")
    history_size: int = 1000
    dial_timeout: float = 10.0
    log_level: str = "info"
    quiet: bool = False


def load_config(overrides: dict | None = None) -> Config:
    cfg = Config()
    config_path = Path.home() / ".tcpsh.yaml"
    if config_path.exists():
        with config_path.open() as f:
            data = yaml.safe_load(f) or {}
        if "prompt" in data:
            cfg.prompt = data["prompt"]
        if "history_file" in data:
            cfg.history_file = os.path.expanduser(data["history_file"])
        if "history_size" in data:
            cfg.history_size = int(data["history_size"])
        if "dial_timeout" in data:
            cfg.dial_timeout = float(data["dial_timeout"])
        if "log_level" in data:
            cfg.log_level = data["log_level"]
        if "quiet" in data:
            cfg.quiet = bool(data["quiet"])

    if overrides:
        for k, v in overrides.items():
            if hasattr(cfg, k) and v is not None:
                setattr(cfg, k, v)
    return cfg
