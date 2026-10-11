# Architecture and implementation decisions

## Boundaries

```mermaid
flowchart LR
  CMD[CMD wrapper] --> CLI[Core CLI]
  PS[PowerShell module] --> CLI
  UI[Qt / xterm.js] --> PTY[ConPTY shell]
  UI --> E[Hybrid Engine]
  CLI --> E
  E --> L[Local rules]
  E --> O[Ollama loopback]
  L --> V[Pydantic Plan]
  O --> V
  V --> R[Independent RiskEngine]
  R --> X[Parent shell / PTY execution]
```

Core, providers, typed schema, configuration and policy do not call Windows APIs. `PlatformAdapter`, `ShellAdapter`, `PtyBackend` define replacement boundaries. Windows lives under `platform/windows`; Linux is deliberately not implemented.

## Research, verified 2026-10-10

| Subject | Decision / official source |
|---|---|
| Parent shell | A child cannot change its parent cwd. CMD calls a batch action in the current interpreter. [Microsoft CALL](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/call) |
| PowerShell | Use a module function importing a structured plan. Add one marked block to CurrentUserAllHosts, preserving existing bytes and backups. Discover `$PROFILE` in each installed shell. [Profiles](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles) |
| PTY | pywinpty 3.0.3 explicitly selects native ConPTY, not legacy winpty. One shell process per window; blocking reads run on a dedicated thread. [pywinpty](https://github.com/andfoy/pywinpty), [ConPTY lifecycle](https://learn.microsoft.com/en-us/windows/console/creating-a-pseudoconsole-session) |
| Renderer | xterm.js 5.5.0 with Fit/WebLinks addons vendored from pinned npm dependencies. QWebEngine/QWebChannel local files only. [xterm security](https://xtermjs.org/docs/guides/security/), [Qt WebChannel](https://doc.qt.io/qtforpython-6/PySide6/QtWebChannel/QWebChannel.html) |
| Prompt markers | OSC title (`0`) carrying a random per-window token and cwd, emitted after the prompt. ConPTY reliably carries this supported OSC. Unknown custom OSC sequences can be dropped by the Windows console. [Windows VT](https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences) |
| Structured output | Pass Pydantic JSON Schema to `/api/chat.format`, temperature 0, `think:false`, bounded context, one retry on invalid schema. [Ollama structured output](https://docs.ollama.com/capabilities/structured-outputs) |
| Model | Exact requested default `qwen3:4b-instruct`, official tag approx. 2.5 GB Q4_K_M. No silent tag substitution. [Ollama model](https://ollama.com/library/qwen3:4b-instruct) |

## Typed actions instead of unvalidated strings

In 0.3.0, `inspect` plans expose read-only read/list/find/processes tools for questions about actual files. Engine executes bounded observations in the current/known directories, then calls Qwen again with structured, redacted evidence. The answer phase allows explain/clarify/error and removes action fields, preventing repeated inspection rounds. Tool results and file contents remain untrusted data. Trace metadata comes from the actual Ollama response, never the model-authored plan. `--model` or the GUI route selector can bypass concrete local rules; the independent risk check and confirmation still apply.

Plans contain `actions`, rather than treating a list of free-form commands as authoritative. Navigation, file queries (size, date, pattern and file type), process RAM queries, reading, deletion, clearing and environment changes have typed fields. Quoting happens in the shell adapter. Complex filesystem/process queries invoke Chameleon's trusted read-only query helper using an ASCII base64 JSON argument, so CMD does not need an AI-generated nested interpreter. A `command` escape hatch remains subject to a conservative independent allowlist and confirmation. Opaque interpreters/downloads/storage destruction are blocked. This deliberately uses a more restrictive schema than the conceptual example to make paths/data distinguishable from executable syntax.

The generation schema requires the full plan envelope, fixes the target shell and exposes only relevant fields for each action kind. Clearly worded file searches use a file-query grammar; Qwen still interprets their pattern, path, size and date constraints. This avoids the 4B model dropping optional filters or substituting a process operation for a file search. Invalid output gets one corrective retry including validation errors, and is never executed.

Model context removes terminal escape sequences, caps visible recent output at 600 characters and includes only relevant executable paths. This bounds privacy exposure and CPU prompt-processing latency. General language preference is reserved for future UI translation; the initial UI uses Spanish with conventional terminal labels, while natural requests support Spanish and English now.

## Input and interactive programs

All editing keys go to the real shell. On Enter, xterm reads the complete rendered shell line using public buffer APIs. If an authenticated prompt marker is active, the bridge classifies the line; known commands go to ConPTY immediately. Natural input is held while local rules or Ollama plan it. Generated commands are inserted into the same shell after clearing its editable line; input echo is suppressed until its completion boundary. A marker is inactive after Enter until the real shell emits another prompt, so REPL/SSH/TUI input stays raw. Multiline paste always stays raw. Shell aliases/functions/cmdlets are discovered inside PowerShell's prompt. A user who changes/removes the child prompt marker gets a raw terminal until starting a new session.

## Threading and shutdown

PTY reader and AI workers do not call widgets. Qt signals marshal results to the UI thread. Async HTTP has timeout and cancellation. Ctrl+C while inference is running cancels its task and returns the shell prompt. Shutdown terminates child processes before the shell, cancels PTY IO and bounds reader joining. QWebEngine prevents automatic remote navigation and network access from local content. Explicit clicked hyperlinks can open the user's browser.

## Distribution and updates

PyInstaller onedir shares Qt/Python among console Core and windowed Terminal/Setup. A small standard-library bootstrap embeds the release ZIP and starts the full PySide Setup from a random temporary directory. This avoids duplicating Qt inside the installer and supports repair without holding installed DLLs open. Setup can be run again with a newer release for Update. Version is semantic `0.1.0`; no update server or background downloader exists. Releases can add signing without changing core interfaces.

The build limits dependency scanning to Windows and the Python runtime paths, preventing unrelated developer-tool ICU/API shim DLLs from entering Qt's runtime. Before spawning native shells or external programs, Windows temporarily restores the normal DLL search path and removes bundled paths from the child environment, then restores the parent runtime immediately after creation. See [PyInstaller external programs](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application).

pywinpty's side-by-side `conpty.dll` requires its matching `OpenConsole.exe` from the published wheel. The spec explicitly bundles that host because dependency scanning only discovers linked DLLs. Frozen smoke tests catch a missing host by requiring actual shell output, navigation and direct commands. The backend argument uses a nonempty representation of ConPTY's zero constant to prevent pywinpty's environment fallback from selecting legacy WinPTY.
