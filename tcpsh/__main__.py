from __future__ import annotations

import asyncio
import typer

from .config import load_config
from .console import TcpshConsole

app = typer.Typer(add_completion=False)


@app.command()
def main(
    port: int = typer.Option(
        None, "-p", "--port", help="Open this port immediately on start"
    ),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Suppress banner"),
) -> None:
    """Interactive TCP connection manager."""
    cfg = load_config({"quiet": quiet})
    console = TcpshConsole(cfg)
    asyncio.run(console.run())


if __name__ == "__main__":
    app()
