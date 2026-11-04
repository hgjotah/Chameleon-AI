# Chameleon AI · Chameleon Terminal

<img src="src/chameleon/assets/icons/chameleon.png" alt="Chameleon Terminal logo" width="140">

A local assistant for **Windows 10 1809+ and Windows 11 x64**, written in Python 3.13, using Ollama and `qwen3:4b-instruct`. It turns English or Spanish requests into validated actions in your current session. Includes a real graphical terminal: PySide6, ConPTY and locally bundled xterm.js.

```cmd
chameleon ai go to Downloads
chameleon ai list pdf
chameleon ai find pdf
chameleon ai create a file named notes.txt with content "Hello"
chameleon ai create a folder named project
chameleon ai copy notes.txt to copy.txt
chameleon ai --dry-run find Python files larger than 1 MB
chameleon ai delete old.txt
chameleon ai delete a file in Downloads named Sample
chameleon ai --force-model summarize notes.txt
chameleon doctor
```

`cd` persists in CMD and PowerShell. Generated commands are hidden except during confirmation, with `--show` or with `--dry-run`. `dir`, `git status`, `python` and all your regular commands continue to use their original shell.

Creating files/folders, reading, copying, moving and navigation use local rules when the request is specific. Create/copy/move never overwrite an existing destination. Balanced asks for confirmation before changes; Full access follows your configuration without application confirmations, except when you explicitly request the `--try` preview. In Chameleon Terminal, type your request directly; in CMD/PowerShell, use `chameleon ai`.

Setup shows Ollama installation, server availability and the downloaded model separately. Keep **Prepare AI and verify the connection** checked to verify all three. Installing missing Ollama requires consent before downloading its official installer. Wait for the real inference test. The terminal can be installed even if downloading fails, but Setup will report **AI pending** and offer Repair.

Qwen reports progress while generating; only a complete, validated response may propose actions. On CPU systems, **Automatic · fast** avoids inference for specific local operations. `--force-model` verifies a real model call. CPU threads are configurable in Settings → Local AI (4 by default); speed also depends on RAM and system load.

Chameleon uses native help and metadata from the installed Windows/shell to review Qwen proposals. It does not add memorized task/answer pairs for test phrases. It distinguishes CMD, Windows PowerShell 5.1 and PowerShell 7, preserves verified operands and corrects invalid parameters or paths before execution. Review can add another inference round. The 0.5B model still has comprehension limits: valid syntax alone does not prove that a command fulfills an arbitrary request. Specific local actions continue to avoid inference.

The application interface, help, diagnostics and app-authored responses are in **English**. English and Spanish requests remain supported. User filenames, literal file content and output from Windows or other programs retain their original language.

## Install and run

1. Run `dist/ChameleonSetup.exe` (self-contained release; Python is not required).
2. Select **Install Chameleon**. If Ollama is missing, allow its official installation and model download. Setup verifies the Ollama signature and a local inference response.
3. If PowerShell blocks profiles, Setup explains the policy and offers **RemoteSigned CurrentUser** with explicit consent. It never silently changes policies.
4. Open a **new** CMD or PowerShell window and use `chameleon ai ...`.
5. Open **Chameleon Terminal**, **Chameleon Settings** or **Uninstall Chameleon** from Start.

Per-user installation: `%LOCALAPPDATA%\ChameleonAI`. Existing PATH entries are preserved. Command Processor AutoRun is not used. Ollama and model weights are not bundled inside the installer.

## Chameleon Terminal

CMD is the default. Open another session using the shell selector or **+**. Interactive programs receive direct input. At the main prompt, enter `Downloads` or a natural-language request. Recognized commands, aliases and scripts go directly to the PTY. **Direct input** forces native input when needed. **Guide** shows examples; **Settings** controls fonts, cursor, AI and privacy.

Shortcuts: Ctrl+C interrupts/cancels AI; Ctrl+Break works where the process supports it; Ctrl+Shift+C/V copies/pastes; Ctrl+`+`/`-` changes font size; F11 toggles full screen. The real shell handles arrows, Tab and history. Multiline paste always uses direct input. For English requests starting with a native command name such as `copy` or `find`, use the explicit `chameleon ai` prefix to avoid ambiguity.

## `chameleon ai` commands (since 0.7.0)

Use these in CMD, PowerShell or Chameleon Terminal:

| Command | Result |
|---|---|
| `chameleon ai --version` | Show the Chameleon version you are running. |
| `chameleon ai --model` | Show the configured model and whether AI is enabled, without calling the model. |
| `chameleon ai --models` | List downloaded local Ollama model tags and mark the current selection. |
| `chameleon ai --changemodel` | Open the downloaded-model selector. Use ↑/↓ and Enter to choose; Esc or Ctrl+C cancels. |
| `chameleon ai --changemodel qwen2.5:0.5b` | Save this tag directly if it is downloaded and verified as local. |
| `chameleon ai --help` | Show all public commands and options. |
| `chameleon ai --try <request>` | Show the actual command for your shell and offer **Cancel** or **Run** in the current session. |
| `chameleon ai --dry-run <request>` | Show the proposal without executing it or offering execution. |
| `chameleon ai --show <request>` | Show the generated command, then follow normal permissions and execution behavior. |
| `chameleon ai --force-model <request>` | Force a model call, even for requests normally handled by local rules. |
| `chameleon ai --debug <request>` | Show proposal source and diagnostics; normal execution behavior still applies. |

```powershell
chameleon ai --try go to Desktop
chameleon ai --force-model --try list files
chameleon ai --changemodel
```

`--try` shows the folder, shell, actual proposal source and command to execute. **Cancel** is selected initially: Enter alone does not run anything. Move to **Run** and press Enter to approve. This confirmation also applies with **Full access**; an action blocked by your permissions cannot be approved here. Without an interactive console, the proposal is displayed but never executed. Routing follows your local-rule/model configuration; combine `--force-model --try` to require real inference. Do not combine `--try` and `--dry-run`.

Model changes are saved for subsequent `chameleon ai` calls and new Chameleon Terminal windows. The list comes from local Ollama; if it does not respond, Chameleon reports the problem without changing the selection. Prepare missing models in Setup or Settings → Local AI; the selector does not install or download software. For compatibility, `--model` **followed by a request** retains its earlier force-model behavior; used alone, it shows the current selection.

## AI, privacy and safety

Open **AI and permissions** to see session controls. The panel shows the response, source, model, calls, tokens and actual duration. **Automatic · fast** uses specific local rules and Qwen for other requests. **Qwen · always**, CLI `--force-model`, or the Settings preference forces the model for natural-language requests; normal commands retain direct input.

The default response is **the command only**, without JSON, greetings, Markdown or explanations. Chameleon favors the shortest direct native command. It validates formatting, checks suspicious cmdlets and simple read/delete sources, and makes bounded corrections when the model invents a command or path. In this mode, data is read when the command executes, without sending file contents to the model. Disable this setting to use the structured planner and inspection tools.

Choose **qwen3:4b-instruct** (~2.5 GB) or **qwen2.5:0.5b** (~398 MB) in Setup, Settings or the terminal panel. In Settings, enter another local tag and select **Download if missing and test model**. The smaller model uses fewer resources and may make more mistakes; Chameleon never silently substitutes another model.

Extensionless names are matched against actual files in the requested folder. If there is exactly one `Sample.txt`, “delete Sample” proposes it; multiple candidates require an exact path. `Downloads`, its Spanish alias `Descargas`, and subfolders resolve through actual Windows known folders, including redirected locations.

Inference contacts only `http://127.0.0.1:11434`, without proxies or cloud fallback. Clear local rules work even when Ollama is offline. xterm.js and all resources are bundled; after downloading Ollama and the model, Internet access is unnecessary for local inference.

There is no telemetry. Permanent history is **off** by default. External session context is limited to six redacted items, expires after 30 minutes and checks PID plus process creation time to prevent PID reuse. It does not monitor ordinary commands in external terminals. The GUI keeps only a bounded output tail in memory. Secret redaction is basic, not infallible.

Choose access in **Settings → Model access**: Read only, Balanced, Developer, Custom or Full access. Custom offers separate read, write, delete, command, script, network, system and confirmation controls. Balanced is the default; Developer allows arbitrary execution with confirmation. **Full access removes Chameleon blocks and confirmations**, using your existing Windows user permissions. It does not elevate privileges or bypass UAC/ACLs. These controls are application policy, not an OS sandbox; arbitrary scripts require all effect permissions because they can perform any of those operations. Manually typed commands remain under your control. Explicit `--try` requests always require approval.

The interface uses forest, moss and sage greens, matte surfaces and glass reserved for action bars. The AI panel opens on demand without resizing the terminal. Setup groups advanced options and details into expandable controls. Buttons adapt MIT-licensed [Codrops MagneticButtons](https://github.com/codrops/MagneticButtons) and [Motion Primitives Spotlight](https://github.com/ibelick/motion-primitives), with magnetic motion, radial lighting and reversible transitions. Windows reduced-motion preferences are respected and timers stop at rest. Original sources and pinned revisions are in `src/chameleon/assets/licenses/ui-motion/PROVENANCE.md`.

Liquid Glass reuses the MIT optical renderer/compositor from [PyGlass](https://github.com/neomosh8/pyglass), adapted to PySide6. Backdrop pixels come exclusively from the application. Glass rendering is cached and resolution-limited to reduce CPU/RAM. Licenses and exact revisions are bundled.

## Build from source

Development requirements: Python **3.13 x64**, Node.js 22+ and Windows. Destination computers do not need these development tools.

```powershell
.\scripts\build.ps1
```

The script installs pinned dependencies, checks lint/types/tests, copies local npm resources, generates icons and builds:

```text
dist/ChameleonSetup.exe                 Self-contained installer
dist/Chameleon/ChameleonCore.exe        CLI and shell protocol
dist/Chameleon/ChameleonTerminal.exe    GUI
dist/Chameleon/ChameleonSetup.exe       Setup / Settings / Uninstall
dist/Chameleon/_internal/               Shared runtime (keep the complete folder)
dist/ChameleonAI-0.7.1-windows-x64.zip   Portable package with integrated Setup
dist/ChameleonAI-0.7.1-source.zip        Source ready for GitHub
dist/SHA256SUMS.json                    Checksums
```

After preparing `.venv`, run from source with `scripts/run.ps1 terminal`, `scripts/run.ps1 setup` or `scripts/run.ps1 settings`. `python -m chameleon ai --dry-run ...` previews plans; only the installed wrapper/module can change parent-shell state.
