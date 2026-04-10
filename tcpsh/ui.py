from __future__ import annotations

import io

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import ANSI
from rich.console import Console as RichConsole
from rich.table import Table
from rich import box


# Used only to render tables to a string buffer; output goes via _pt_print.
def _rich_render(renderable) -> str:
    buf = io.StringIO()
    tmp = RichConsole(file=buf, force_terminal=True)
    tmp.print(renderable)
    return buf.getvalue()


BANNER = r"""
  _                 _
 | |_ ___ _ __  ___| |__
 | __/ __| '_ \/ __| '_ \
 | || (__| |_) \__ \ | | |
  \__\___| .__/|___/_| |_|
         |_|
"""

# ANSI codes used in messages
_R = "\x1b[0m"  # reset
_CYAN = "\x1b[36m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"
_BOLD = "\x1b[1m"


def _pt_print(text: str) -> None:
    """Print via prompt_toolkit so ANSI sequences survive patch_stdout()."""
    print_formatted_text(ANSI(text))


def banner() -> None:
    _pt_print(f"{_CYAN}{BANNER}{_R}")


def info(msg: str) -> None:
    _pt_print(f"{_BOLD}{_GREEN}[+]{_R} {msg}")


def warn(msg: str) -> None:
    _pt_print(f"{_BOLD}{_YELLOW}[!]{_R} {msg}")


def error(msg: str) -> None:
    _pt_print(f"{_BOLD}{_RED}[-]{_R} {msg}")


def plain(msg: str) -> None:
    _pt_print(msg)


def _state_style(state: str) -> str:
    return {
        "active": "[green]active[/green]",
        "foreground": "[cyan]foreground[/cyan]",
        "background": "[yellow]background[/yellow]",
        "dead": "[red]dead[/red]",
    }.get(state, state)


def render_ports(ports: list[dict]) -> None:
    if not ports:
        _pt_print("  No open ports")
        return
    t = Table(box=box.SIMPLE, show_header=True)
    t.add_column("PORT", style="bold")
    t.add_column("HOST")
    for p in ports:
        t.add_row(str(p["port"]), p["host"])
    _pt_print(_rich_render(t))


def render_sessions(sessions: list) -> None:
    if not sessions:
        _pt_print("  No active sessions")
        return
    t = Table(box=box.SIMPLE, show_header=True)
    t.add_column("ID", style="bold")
    t.add_column("PORT")
    t.add_column("REMOTE")
    t.add_column("STATE")
    t.add_column("TX", justify="right")
    t.add_column("RX", justify="right")
    for s in sessions:
        t.add_row(
            str(s.id),
            str(s.port),
            s.remote,
            _state_style(s.state.value),
            f"{s.bytes_tx/1024:.1f}k",
            f"{s.bytes_rx/1024:.1f}k",
        )
    _pt_print(_rich_render(t))


def render_forwards(entries: list[dict]) -> None:
    if not entries:
        _pt_print("  No active forwards/proxies")
        return
    t = Table(box=box.SIMPLE, show_header=True)
    t.add_column("TYPE", style="bold")
    t.add_column("PORT")
    t.add_column("REMOTE")
    t.add_column("LOG")
    for e in entries:
        kind_style = (
            "[magenta]proxy[/magenta]" if e["type"] == "proxy" else "[blue]fwd[/blue]"
        )
        t.add_row(
            kind_style,
            str(e["local_port"]),
            e["remote"],
            e["log_file"] or "-",
        )
    _pt_print(_rich_render(t))
