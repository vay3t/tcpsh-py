from __future__ import annotations

import asyncio
import subprocess


async def exec_local(cmd: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "bash",
        "-c",
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL,
    )
    stdout, stderr = await proc.communicate()
    return (stdout + stderr).decode(errors="replace")
