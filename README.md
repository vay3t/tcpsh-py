# tcpsh — Interactive TCP Connection Manager (Python)

> **Disclaimer:** This project is a **proof of concept**. It is not production-ready and does not guarantee compatibility or correct operation with MCP (Model Context Protocol) or any MCP-based tooling. Use at your own risk.

Python port of `tcpsh`. Full async TCP server management from a `prompt_toolkit`-powered REPL, with `rich` tables for output, forwarding, proxying, and per-session interaction.

---

## Requirements

- Python ≥ 3.10 (uses `match` statement)
- pip or pipx

---

## Installation

### With pipx (recommended)

[pipx](https://pipx.pypa.io) installs the tool in an isolated environment and exposes the `tcpsh` command globally:

```bash
pipx install git+<repo-url>
```

Or from a local clone:
```bash
git clone <repo-url> tcpsh-py
pipx install ./tcpsh-py
```

Run:
```bash
tcpsh
```

Upgrade later with:
```bash
pipx upgrade tcpsh
```

### With venv + pip

```bash
git clone <repo-url> tcpsh-py
cd tcpsh-py

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or install dependencies only (without editable install):
```bash
pip install -r requirements.txt
```

Run:
```bash
python3 -m tcpsh
# or, after editable install:
tcpsh
```

---

## Quick Start

```
$ python3 -m tcpsh

  _                 _
 | |_ ___ _ __  ___| |__
 | __/ __| '_ \/ __| '_ \
 | || (__| |_) \__ \ | | |
  \__\___| .__/|___/_| |_|
         |_|
         
tcpsh> open 4444
[+] Listening on 0.0.0.0:4444

# From another terminal: nc localhost 4444
[+] New connection on :4444 from 127.0.0.1:55234 (session 1)

tcpsh> use 4444
[+] Entering session 1 (127.0.0.1:55234). Type '+back' to return...
[4444]>
```

---

## CLI Options

| Option | Description |
|---|---|
| `-p / --port <port>` | Open a port immediately on startup |
| `-q / --quiet` | Suppress the banner |
| `--help` | Show CLI help |

---

## Usage

### Opening Ports

```
tcpsh> open 4444
tcpsh> open 443 127.0.0.1
```

### Listing Resources

```
tcpsh> list ports
tcpsh> list conn
tcpsh> list fwd
tcpsh> list proxy
tcpsh> list all
```

### Interacting with a Session

```
tcpsh> use 4444          # auto-select first session
tcpsh> use 4444:2        # session #2 on port 4444

[4444]> id               # sent to TCP connection
[4444]> +back            # return to menu
```

### Port Forwarding

```
tcpsh> fwd 8080 10.0.0.1:80
tcpsh> fwd list
tcpsh> fwd close 8080
```

### TCP Proxy

```
tcpsh> proxy 8080 10.0.0.1:80
tcpsh> proxy 8080 10.0.0.1:80 /tmp/traffic.log
tcpsh> proxy log 8080 /tmp/new.log
tcpsh> proxy list
tcpsh> proxy close 8080
```

### Local Commands

```
tcpsh> !ifconfig
[4444]> !id
```

---

## Command Reference

| Command | Description |
|---|---|
| `open <port> [host]` | Open TCP listener |
| `close <port>` | Close listener |
| `kill [-f] <port>[:<idx>]` | Terminate session (`-f` = force RST) |
| `use <port>[:<idx>]` | Attach to session |
| `info <port>[:<idx>]` | Session details |
| `list ports\|conn\|fwd\|proxy\|all` | List resources |
| `fwd <lport> <host:rport>` | Start TCP forward |
| `fwd list\|close <lport>` | Manage forwards |
| `proxy <lport> <host:rport> [file]` | Start TCP proxy |
| `proxy list\|close\|log` | Manage proxies |
| `!<cmd>` | Local system command |
| `help` | Show help |
| `clear` | Clear terminal |
| `exit` | Quit |

### Special Session Commands

| Command | Effect |
|---|---|
| `+back` | Return to menu (connection stays open) |
| `+bg` / `+background` | Background the session |
| `+exit` | Exit tcpsh |
| `!<cmd>` | Run local command |

---

## Configuration

Create `~/.tcpsh.yaml`:

```yaml
prompt: "tcpsh> "
history_file: "~/.tcpsh_history"
history_size: 1000
dial_timeout: 10
log_level: "info"
quiet: false
```

---

## Signal Handling

| Signal | Behaviour |
|---|---|
| `Ctrl+C` (SIGINT) | Prints a tip — does **not** close connections |
| `SIGTERM` | Graceful shutdown |

---

## Project Structure

```
tcpsh/
├── __init__.py
├── __main__.py           CLI entrypoint (typer)
├── config.py             Config loading from ~/.tcpsh.yaml
├── parser.py             Command parser (tool/system/special/passthrough)
├── executor.py           Local shell command execution (asyncio subprocess)
├── ui.py                 rich-based output helpers + table renderers
├── console.py            Async REPL loop + command dispatcher
├── session/
│   ├── state.py          State enum
│   ├── session.py        Session wrapper around asyncio streams
│   └── manager.py        Thread-safe session registry
├── listener/
│   ├── listener.py       asyncio.start_server wrapper + event callbacks
│   └── manager.py        Listener lifecycle management
└── forward/
    ├── forwarder.py      Transparent async TCP pipe
    ├── proxy.py          Async TCP pipe + traffic logging
    └── manager.py        Forward/proxy registry
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `prompt_toolkit` | REPL with history, Ctrl+R, autocomplete |
| `rich` | Terminal tables and colored output |
| `typer` | CLI flag parsing |
| `pyyaml` | Config file parsing |

Install:
```bash
pip install prompt_toolkit rich typer pyyaml
```

---

## License

MIT
