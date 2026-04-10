from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout

from .config import Config
from .listener.manager import ListenerManager
from .session.manager import SessionManager
from .session.state import State
from .forward.manager import ForwardManager
from .executor import exec_local
from .parser import parse, parse_port_idx, parse_remote
from . import ui

HELP_TEXT = """
Commands:
  open <port> [host]              Open TCP listener
  close <port>                    Close listener and its sessions
  kill [-f] <port>[:<idx>]        Terminate session (FIN; -f for RST)
  use <port>[:<idx>]              Attach to session
  info <port>[:<idx>]             Show session details
  list ports|conn|fwd|proxy|all   List resources
  fwd <lport> <host:rport>        Transparent TCP forward
  fwd list|close <lport>          Manage forwards
  proxy <lport> <host:rport> [f]  TCP proxy with traffic logging
  proxy list|close|log            Manage proxies
  !<cmd>                          Run local system command
  help                            Show this help
  clear                           Clear terminal
  exit                            Quit

Session mode (+back to return):
  +back / +bg  Return / send to background
  +exit        Exit tcpsh
  !<cmd>       Run local command
  (anything else is sent to the remote connection)
"""


class TcpshConsole:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._listeners = ListenerManager()
        self._sessions = SessionManager()
        self._forwards = ForwardManager()
        self._active_sess = None
        self._session_mode = False
        self._prompt_sess: PromptSession | None = None

    async def run(self) -> None:
        if not self._cfg.quiet:
            ui.banner()

        self._listeners.on_event(self._on_listener_event)

        history = FileHistory(str(Path(self._cfg.history_file).expanduser()))
        self._prompt_sess = PromptSession(history=history)

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, self._on_sigint)
        loop.add_signal_handler(
            signal.SIGTERM, lambda: asyncio.ensure_future(self._shutdown())
        )

        await self._repl()

    # ── REPL ─────────────────────────────────────────────────────────────

    async def _repl(self) -> None:
        with patch_stdout():
            while True:
                prompt = (
                    f"[{self._active_sess.port}]> "
                    if self._session_mode
                    else self._cfg.prompt
                )
                try:
                    line = await self._prompt_sess.prompt_async(prompt)
                except (KeyboardInterrupt, EOFError):
                    await self._shutdown()
                    return

                cmd = parse(line, self._session_mode)

                if cmd.kind == "empty":
                    continue
                elif cmd.kind == "special":
                    await self._handle_special(cmd.verb)
                elif cmd.kind == "system":
                    out = await exec_local(cmd.raw)
                    print(out, end="")
                elif cmd.kind == "passthrough":
                    if self._active_sess:
                        await self._active_sess.write(cmd.raw + "\n")
                elif cmd.kind == "tool":
                    await self._dispatch(cmd)

    # ── Events ───────────────────────────────────────────────────────────

    async def _on_listener_event(self, event: str, payload: object) -> None:
        if event == "connection":
            sess = payload
            self._sessions.add(sess)
            ui.info(
                f"New connection on :{sess.port} from {sess.remote} (session {sess.id})"
            )
        elif event == "session_close":
            sess = payload
            if self._active_sess and self._active_sess.id == sess.id:
                ui.error(f"Session {sess.id} disconnected (remote closed)")
                self._leave_session()
            else:
                ui.error(f"Session {sess.id} ({sess.remote}) disconnected")
            self._sessions.remove(sess.id)
        elif event == "data":
            sess, chunk = payload
            if (
                self._active_sess
                and self._active_sess.id == sess.id
                and self._session_mode
            ):
                (sys.__stdout__ or sys.stdout).write(chunk.decode(errors="replace"))
                (sys.__stdout__ or sys.stdout).flush()

    # ── Signal handling ───────────────────────────────────────────────────

    def _on_sigint(self) -> None:
        if self._session_mode:
            ui.warn("Use '+back' to return to menu or '+exit' to quit.")
        else:
            ui.warn("Type 'exit' to quit. Active connections are NOT affected.")

    # ── Special commands ─────────────────────────────────────────────────

    async def _handle_special(self, verb: str) -> None:
        if verb in ("back", "bg", "background"):
            if self._active_sess:
                self._active_sess.state = State.BACKGROUND
                self._leave_session()
        elif verb == "exit":
            await self._shutdown()
        else:
            ui.error(f"Unknown special command: +{verb}")

    def _leave_session(self) -> None:
        self._active_sess = None
        self._session_mode = False

    # ── Dispatcher ───────────────────────────────────────────────────────

    async def _dispatch(self, cmd) -> None:
        try:
            match cmd.verb:
                case "open":
                    await self._do_open(cmd.args)
                case "close":
                    await self._do_close(cmd.args)
                case "kill":
                    await self._do_kill(cmd.args)
                case "use":
                    await self._do_use(cmd.args)
                case "list":
                    self._do_list(cmd.args)
                case "fwd":
                    await self._do_fwd(cmd.args)
                case "proxy":
                    await self._do_proxy(cmd.args)
                case "info":
                    self._do_info(cmd.args)
                case "help":
                    ui.plain(HELP_TEXT)
                case "clear":
                    out = sys.__stdout__ or sys.stdout
                    out.write("\033c")
                    out.flush()
                case "exit":
                    await self._shutdown()
                case _:
                    ui.error(f"Unknown command: {cmd.verb}. Type 'help' for usage.")
        except Exception as exc:
            ui.error(str(exc))

    # ── Command handlers ─────────────────────────────────────────────────

    async def _do_open(self, args: list[str]) -> None:
        if not args:
            ui.error("Usage: open <port> [host]")
            return
        host = args[1] if len(args) > 1 else "0.0.0.0"
        port = int(args[0])
        await self._listeners.open(port, host)
        ui.info(f"Listening on {host}:{port}")

    async def _do_close(self, args: list[str]) -> None:
        if not args:
            ui.error("Usage: close <port>")
            return
        port = int(args[0])
        await self._listeners.close(port)
        ui.info(f"Listener :{port} closed")

    async def _do_kill(self, args: list[str]) -> None:
        force = False
        target_str: str | None = None
        rest = list(args)
        if rest and rest[0] == "-f":
            force = True
            rest.pop(0)
        if rest:
            target_str = rest[0]
        if not target_str:
            ui.error("Usage: kill [-f] <port>[:<idx>]")
            return
        parsed = parse_port_idx(target_str)
        if parsed is None:
            ui.error("Invalid port/index")
            return
        port, idx = parsed
        sessions = self._sessions.by_port(port)
        if idx < 1 or idx > len(sessions):
            ui.error("Session not found")
            return
        sess = sessions[idx - 1]
        if force:
            sess.force_close()
        else:
            sess.close()
        ui.info(f"Session {sess.id} terminated")

    async def _do_use(self, args: list[str]) -> None:
        if not args:
            ui.error("Usage: use <port>[:<idx>]")
            return
        parsed = parse_port_idx(args[0])
        if parsed is None:
            ui.error("Invalid port/index")
            return
        port, idx = parsed
        sessions = self._sessions.by_port(port)
        if idx < 1 or idx > len(sessions):
            ui.error("No session found")
            return
        sess = sessions[idx - 1]
        self._active_sess = sess
        self._session_mode = True
        sess.state = State.FOREGROUND
        ui.info(
            f"Entering session {sess.id} ({sess.remote}). Type '+back' to return, '+bg' for background, '+exit' to quit."
        )

    def _do_list(self, args: list[str]) -> None:
        sub = args[0] if args else "all"
        if sub == "ports":
            ports = [
                {"port": p, "host": (self._listeners.get_listener(p).host or "0.0.0.0")}
                for p in self._listeners.open_ports()
            ]
            ui.render_ports(ports)
        elif sub == "conn":
            ui.render_sessions(self._sessions.all())
        elif sub == "fwd":
            ui.render_forwards([e for e in self._forwards.list() if e["type"] == "fwd"])
        elif sub == "proxy":
            ui.render_forwards(
                [e for e in self._forwards.list() if e["type"] == "proxy"]
            )
        else:
            ports = [
                {"port": p, "host": (self._listeners.get_listener(p).host or "0.0.0.0")}
                for p in self._listeners.open_ports()
            ]
            ui.plain("--- Ports ---")
            ui.render_ports(ports)
            ui.plain("--- Sessions ---")
            ui.render_sessions(self._sessions.all())
            ui.plain("--- Forwards / Proxies ---")
            ui.render_forwards(self._forwards.list())

    async def _do_fwd(self, args: list[str]) -> None:
        if not args or args[0] == "list":
            ui.render_forwards([e for e in self._forwards.list() if e["type"] == "fwd"])
            return
        if args[0] == "close":
            if len(args) < 2:
                ui.error("Usage: fwd close <lport>")
                return
            await self._forwards.close(int(args[1]))
            ui.info(f"Forward :{args[1]} removed")
            return
        if len(args) < 2:
            ui.error("Usage: fwd <lport> <host:rport>")
            return
        lport = int(args[0])
        remote = parse_remote(args[1])
        if remote is None:
            ui.error("Invalid remote address")
            return
        rhost, rport = remote
        await self._forwards.open_forward(lport, rhost, rport, self._cfg.dial_timeout)
        ui.info(f"Forward  :{lport}  ──►  {rhost}:{rport}")

    async def _do_proxy(self, args: list[str]) -> None:
        if not args or args[0] == "list":
            ui.render_forwards(
                [e for e in self._forwards.list() if e["type"] == "proxy"]
            )
            return
        if args[0] == "close":
            if len(args) < 2:
                ui.error("Usage: proxy close <lport>")
                return
            await self._forwards.close(int(args[1]))
            ui.info(f"Proxy :{args[1]} removed")
            return
        if args[0] == "log":
            if len(args) < 3:
                ui.error("Usage: proxy log <lport> <file>")
                return
            self._forwards.set_proxy_log(int(args[1]), args[2])
            ui.info(f"Proxy :{args[1]} log → {args[2]}")
            return
        if len(args) < 2:
            ui.error("Usage: proxy <lport> <host:rport> [logfile]")
            return
        lport = int(args[0])
        remote = parse_remote(args[1])
        log_file = args[2] if len(args) > 2 else None
        if remote is None:
            ui.error("Invalid remote address")
            return
        rhost, rport = remote
        await self._forwards.open_proxy(
            lport, rhost, rport, log_file, self._cfg.dial_timeout
        )
        ui.info(
            f"Proxy    :{lport}  ──►  {rhost}:{rport}"
            + (f"  log→{log_file}" if log_file else "")
        )

    def _do_info(self, args: list[str]) -> None:
        if not args:
            ui.error("Usage: info <port>[:<idx>]")
            return
        parsed = parse_port_idx(args[0])
        if parsed is None:
            ui.error("Invalid target")
            return
        port, idx = parsed
        sessions = self._sessions.by_port(port)
        if idx < 1 or idx > len(sessions):
            ui.error("Session not found")
            return
        s = sessions[idx - 1]
        ui.plain(f"  ID:      {s.id}")
        ui.plain(f"  Port:    {s.port}")
        ui.plain(f"  Remote:  {s.remote}")
        ui.plain(f"  State:   {s.state.value}")
        ui.plain(f"  TX:      {s.bytes_tx} bytes")
        ui.plain(f"  RX:      {s.bytes_rx} bytes")
        ui.plain(f"  Since:   {s.created_at.isoformat()}")

    # ── Shutdown ─────────────────────────────────────────────────────────

    async def _shutdown(self) -> None:
        active = self._sessions.all()
        if active:
            ui.warn(f"Closing {len(active)} active session(s)…")
        self._sessions.close_all()
        await self._listeners.close_all()
        await self._forwards.close_all()
        raise SystemExit(0)
