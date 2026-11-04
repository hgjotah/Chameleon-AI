# Requirements coverage

This table locates the implementation of all 55 sections of the requirements document. Executed evidence and outstanding manual checks are distinguished in [VALIDATION.md](VALIDATION.md); a function's existence does not certify every Windows version or interactive program.

| Section | Implementation / documentation |
|---|---|
| 1 · Assistant in the current session | CLI, CMD wrapper and PowerShell module; real parent-cwd tests |
| 2 · Real graphical terminal | `terminal/`, `platform/windows/conpty.py`, bundled xterm |
| 3 · Modern Python | Python 3.13, Pydantic, PySide6; `pyproject.toml` |
| 4 · Local AI | `llm/ollama.py`, exact default `qwen3:4b-instruct` |
| 5 · Rules without AI | `core/intents.py`, unambiguous navigation and queries |
| 6 · Normal commands | Builtin, PATH, script and alias classification; direct input |
| 7 · CMD | `assets/shell/chameleon.cmd`, temporary action protocol; no AutoRun |
| 8 · PowerShell | `Chameleon.psm1`, discovered profiles and marked block |
| 9 · Administrator | Inherited token, privilege checks; no automatic elevation |
| 10 · Structured response | `core/schemas.py`, typed actions validated before execution |
| 11 · System prompt | `llm/prompts.py`, contextual schema and no visible reasoning |
| 12 · Context | `core/context.py`; bounded, redacted context |
| 13 · Sessions | `core/sessions.py`; PID + creation time + expiration |
| 14 · Privacy | Opt-in history and redaction; PRIVACY.md |
| 15 · Safety Engine | `safety/engine.py`; model-independent SAFE / CONFIRM / BLOCKED |
| 16 · Ambiguity | `clarify` plan, CLI/GUI selection, safe cancellation |
| 17 · Visibility | Hidden by default, `--show`, `--dry-run`, confirmation preview |
| 18 · GUI behavior | Qt bridge, native editor, classification only at a prompt |
| 19 · Interactive programs | Authenticated OSC marker in child shell; raw REPL/TUI input |
| 20 · Shell selection | CMD default, Windows PowerShell and PowerShell 7 |
| 21 · Appearance | Black/green, system typography, compact bar and AI status |
| 22 · Rendering | xterm 5.5, ANSI, selection, clipboard, scrollback, resize, zoom and F11 |
| 23 · Latency | Local rules, AI worker, PROCESSING indicator and keep-alive |
| 24 · Ollama | Setup, official signature, download progress and inference probe |
| 25 · Offline | Loopback-only inference; VM procedure in VALIDATION.md |
| 26 · Installer | Self-contained Setup, per-user installation, PATH and shortcuts |
| 27 · Repair | Payload copy/verification, integration and AI checks |
| 28 · Uninstall | Ownership manifest; preserves other profile/PATH content; extras require consent |
| 29 · Settings | General, Local AI, Terminal, Model access and Privacy; validation and atomic save |
| 30 · Doctor | `setup/doctor.py`, `chameleon doctor` CLI |
| 31 · Multiple platforms | PlatformAdapter, ShellAdapter, PtyBackend interfaces; Linux reserved |
| 32 · Repository | `src/chameleon`, `tests`, `scripts`, `installer`, `docs`, `.github` |
| 33 · Tests | Parsing, quoting, risk, paths, model, sessions and installation |
| 34 · Real integration | `test_windows_shells.py`, actual CMD / PS 5.1 / PS 7 |
| 35 · Terminal tests | Real ConPTY and GUI; outstanding manual matrix documented |
| 36 · Errors | Actionable diagnostics; invalid plans never execute |
| 37 · Logging | Bounded rotation; prompts/normal output are not saved by default |
| 38 · Configuration | Per-user TOML, typed values and recovery backup |
| 39 · Updates | Semantic versioning, Setup Update using the new release payload |
| 40 · Documentation | README, ARCHITECTURE, BUILDING, INSTALLATION, shell integration, safety and privacy |
| 41 · Build | `scripts/build.ps1`, pinned dependencies, frozen code/payload verification |
| 42 · CI | GitHub Actions on Windows; lint, types, tests, build and executable smoke checks |
| 43 · Quality | Ruff, mypy, separate modules, interfaces and workers |
| 44 · Temporary files | Random names, private ACL, exclusive writes, expiration and cleanup |
| 45 · Protocol | ASCII token in an exclusive file; wrapper never interprets model text |
| 46 · Cancellation | Ctrl+C asyncio cancellation; race test before loop creation |
| 47 · Missing model | AI OFFLINE; shell and local rules remain available |
| 48 · User paths | Windows Known Folders and Windows APIs; no fixed username |
| 49 · Languages | English application UI/messages/docs; English and Spanish requests |
| 50 · Use cases | Navigation, PDF, confirmation, ambiguity, size search and REPL |
| 51 · Exclusions | No cloud, API keys, telemetry, side chat, fake shell or required target Python |
| 52 · Criteria | Build and real component tests; certification limits in VALIDATION.md |
| 53 · Stages | Research, core, integration, AI, safety, GUI, Setup and distribution |
| 54 · Review | Lint, types, tests, executables and packaging issue detection/fixes |
| 55 · Delivery | Source, three executables, standalone Setup, ZIPs, hashes, docs and CI |

Technical decisions differing from the conceptual example—typed actions, query helpers and shared runtime—are explained in ARCHITECTURE.md. Model-generated command text is never considered permission to execute it.
