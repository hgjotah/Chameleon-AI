# Changelog

## 0.7.1 · 2026-11-04

- English application UI, installer, Settings, CLI help, model selector, command previews, diagnostics and app-authored messages.
- English README and remaining project documentation. English and Spanish requests, literal user data, command names and permissions retain their existing behavior.

## 0.7.0 · 2026-11-02

- Version/model information, complete CLI help and a persistent downloaded-model selector with arrow-key navigation.
- Explicit `--try` previews with Cancel selected initially, including Full access; native execution preserves parent-shell state.
- `--models`, `--force-model`, and backward-compatible `--model <request>` behavior. Console modes and cursor visibility are restored after selection/cancellation.

## 0.6.0 · 2026-11-02

- New forest, moss and sage interface: matte surfaces, fewer simultaneous controls and glass reserved for action bars. Original logo preserved.
- Fixed material spectral glow introducing unwanted colors; cache-scaled refraction/bevel, localized lighting and clearer edges.
- Magnetic buttons, text counter-motion, radial lighting and reversible press effects. Native adaptations of MIT Codrops and Motion Primitives code, with original sources, revisions and licenses.
- On-demand AI and permissions panel with transitions; PTY dimensions remain stable and terminal focus returns on close. Escape closes the panel.
- Simplified Setup: expandable advanced options/log, compact status and explicit update action for older versions. Settings navigation and progressive custom permissions.
- Animations stop at rest and when hidden; Windows reduced-motion preference respected. Fresh-install/update checks run in isolated Qt processes.
- Existing models, permissions, commands and configuration preserved.

## 0.5.1 · 2026-11-01

- Grounding in the actual system: shell version/edition/language, executable path, architecture, locale, redirected known folders and allowlisted variables; request-relevant context selection.
- PowerShell 7 correctly identified through the wrapper. Relevant caller aliases/functions and language mode are transmitted without function bodies.
- Native Windows help and PowerShell metadata/AST review operation, parameters, syntax and property values before execution is proposed. Inspection never runs the proposal.
- Removed task/answer pairs from the prompt. The model chooses the command; the application supplies actual observations and native errors for correction.
- Verified simple tasks validate operands, quoting, literal content and operation type; invented names, bare paths and request words used as arguments are rejected.
- Session-property reads and appearance changes use their corresponding permissions without requiring arbitrary script access.
- Ambiguous names and existing destinations are resolved before model invocation. Native context collection runs outside the UI thread.
- One whole-response code delimiter is normalized; prose and multiple lines remain rejected.

## 0.5.0 · 2026-10-31

- Five access profiles: Read only, Balanced, Developer, Custom and Full access without application blocks/confirmations.
- Separate read, write, delete, command, script, network, system and confirmation controls. Arbitrary scripts require all effect permissions; Windows retains authority over privileges and ACLs.
- qwen3:4b-instruct and qwen2.5:0.5b selection in Setup/Settings/Terminal; preparation, download and selected-model testing.
- Default output is a single native command without prose/JSON/Markdown; shell-specific examples, literal path context and retries for unknown cmdlets or invented sources.
- Previous structured planner available by disabling Respond with the command only.
- Real glass refraction based on MIT PyGlass modules, adapted to PySide6/NumPy; pinned attribution/license, bounded cache and no desktop capture.
- Changing model/profile cancels active requests; generation uses a configuration snapshot.
- CMD bridge adapts .cmd/.bat calls and FOR variables for transient batch execution.

## 0.4.0 · 2026-10-11

- Streaming Ollama integration, actual receive progress and rejection of interrupted/truncated responses; cancellation preserves terminal control.
- Automatic local server startup when Ollama is installed but stopped; port checked before launching another server.
- Configurable CPU threads (4 by default), duplicate schema removed from the prompt and concise responses to reduce inference time.
- Summaries with explicit paths perform a real read before a single model call; ambiguous queries retain inspection flow.
- Simple operations forced through Qwen restrict the schema to the relevant action, avoiding nonexistent commands such as `create`.
- Direct file/process queries produce native output; other inspection enters the answer phase, including requests outside initial rules.
- Setup distinguishes Ollama executable, server and model; AI preparation installs a missing backend with consent, downloads the model and requires actual inference.
- Real download percentages, scrollable options and Ollama executable diagnostics; download failures do not conceal successful terminal installation.
- CLI installation with explicit Ollama/model options and exit code 3 when AI remains pending.
- Exact new user-provided image across surfaces, icons and shortcuts; development launchers use the standalone runtime when built.
- Qt bridge registered before renderer loading; removes late registration/initial reload and waits for the client before reading terminal output.

## 0.3.0 · 2026-10-11

- User-provided logo: original PNG in Terminal, Setup, Settings, bootstrap, Windows icons and shortcuts.
- Deletion requests support named files in Downloads and extensionless names; ambiguous candidates require explicit selection.
- Known-folder subpaths and redirected Downloads resolve to actual locations.
- Read-only inspection grounds answers in real files/processes; explicit limits, secret redaction and UTF-16 BOM reading.
- Visible source with actual calls, tokens, model and duration; Automatic/Qwen selector and CLI `--model` option.
- Explicit tool-round closure and bounded summaries prevent repeated inspection and lengthy explanations before action.
- Redesigned Setup/Terminal with response panel, typography, cards, controls and transitions; terminal launch after installation.
- Per-user update through frozen Core preserves preferences, profiles and PATH.
- Runtime permissions applied before staging/backup creation, avoiding an observed update timeout; specific permission diagnostics.

## 0.2.0 · 2026-10-10

- Literal UTF-8 file/folder creation; copy/move without overwriting, shared across CMD, PowerShell and GUI. Explicit UTF-8 reads in PowerShell 5.1.
- Clarifications retain the requested operation; administrative requirements are assessed independently of model suggestions.
- Updated pywinpty to 3.0.5, with event-driven ConPTY shutdown and a fix for the previous CPU loop; all three native binaries explicitly checked.
- PowerShell starts with correct modules even when its parent is PowerShell 7; Doctor no longer reports unknown policies as successful.
- Repair restores binaries, profiles, config, PATH and registry on failure before manifest commit; hashes and atomic manifest.
- Development launcher uses the standalone installer to avoid Microsoft Store Python's private AppData/registry redirection.
- Minimal inference probe; AI failures reported separately from successful terminal installation.
- Renewed native UI: shell/session/guide/path/activity controls, installer states, Settings navigation, animated buttons and transitions.
- Input synchronized with the native editor to prevent Enter truncation; repeated ConPTY titles do not activate AI inside interactive programs.
- Creation tests with Unicode content and symbols in the real terminal, three shell wrappers and distributed executables.

## 0.1.0 · 2026-10-10

- Hybrid English/Spanish core, local Ollama with JSON Schema and Pydantic validation.
- CMD and Windows PowerShell/PowerShell 7 integration preserving session state.
- Independent risk engine, default-negative confirmation and permanent blocking.
- ConPTY terminal with local xterm.js, prompt markers, AI/raw modes and Settings.
- Per-user Setup, Repair, Update and Uninstall; consent-based Ollama/policy management.
- Self-contained Windows build, pytest, ruff, mypy and GitHub Actions.
