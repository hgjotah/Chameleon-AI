# Installation, repair and removal

## Model and access selection

Setup offers qwen3:4b-instruct (~2.5 GB) and qwen2.5:0.5b (~398 MB).
It reuses the selected model if present; otherwise AI preparation downloads it.
Settings → Local AI lets you download/test another local tag and save it.
The terminal's quick selector affects that window. A missing model never causes
an automatic switch to another tag.

Settings → Model access defines profiles and permissions. The quick selector
applies to the session; save the profile in Settings for future CLI processes and
windows. Full access runs without Chameleon blocks/confirmations using your
current Windows rights. Explicit `--try` previews still require approval.
Arbitrary scripts require all effect permissions; application filters are not
a Windows sandbox.

## AI preparation

Setup shows three separate states: Ollama executable installed, local server accessible and model downloaded. **Prepare AI and verify the connection** requires consent to install official Ollama if missing, starts the server, downloads a missing model and verifies a real response. Existing dependencies are reused. An interrupted download leaves AI pending; run **Repair** again. Percentages refer to the current download, not an estimate of the entire installation.

Silent installation through the standalone runtime supports explicit dependency authorization:

```powershell
.\ChameleonCore.exe setup --install --payload . --install-ollama --download-model
```

Without these options, it only reuses existing dependencies. Exit code 3 means the terminal is installed but AI is pending; 0 means preparation completed. Requests start Ollama if it is already installed but stopped; they never download software automatically.

After installing, open CMD from Start in a new window. Consoles and applications opened before installation retain their previous PATH. If you open tabs from an existing Windows Terminal, VS Code or another host, close that host completely and reopen it. Setup notifies Explorer and preserves all other user PATH entries.

Run `ChameleonSetup.exe`. The initial bootstrap extracts only its embedded release into a random temporary directory, starts the PySide installer, waits for exit and removes the temporary payload. The target requires no preinstalled Python.

Install writes `%LOCALAPPDATA%\ChameleonAI\{bin,core,resources,runtime,config,logs}` and an `install.json` ownership manifest. It appends `bin` to the user PATH case-insensitively, sends the Windows Environment change notification, creates Start Menu shortcuts and registers a per-user uninstall entry. No elevation, AutoRun or system PATH modification is used. New terminals load the integration; existing ones keep their previous PATH/profile until restarted.

PowerShell profiles are discovered by launching each installed PowerShell with `-NoProfile` and querying `$PROFILE.CurrentUserAllHosts`, which respects redirected Documents. Existing profiles are backed up before each real change. UTF-8, BOM UTF-8 and BOM UTF-16 profiles retain encoding and original content outside the marked block. If a profile has an incomplete marked block, installation stops with an actionable error instead of discarding content.

## Execution Policy

Restricted or AllSigned prevents loading the unsigned integration. Setup detects this and offers **RemoteSigned for CurrentUser** with an unchecked option and an explicit consent dialog. It never silently changes policy, never attempts to override Group Policy, and records the prior CurrentUser value when it changes it. You may instead retain policy and use CMD/Chameleon Terminal. `-NoProfile` shells do not load the external PowerShell integration; explicitly `Import-Module` if your policy permits it. Do not use a `.cmd` fallback in PowerShell if you need parent-state changes.

## Ollama

Existing Ollama is reused. If absent, Setup offers installation from the official HTTPS URL and checks Authenticode status and Ollama signer before running. Installation requires explicit consent. If automatic installation fails, use [Ollama for Windows](https://ollama.com/download/windows), then run Repair. Setup can start `ollama serve` without a visible console. Model download uses `/api/pull` progress; Ollama verifies content digests. Setup checks tags and performs a structured inference without executing its result.

The inference probe generates only a minimal JSON response after verifying local model metadata. If model download/probing fails, Setup reports **terminal installed, AI pending** and offers retry through Repair. File creation, navigation and direct shell commands remain available. A cold CPU inference can still take tens of seconds; Ctrl+C cancels a GUI request, and Settings exposes the timeout.

## Repair / Update

Close Chameleon Terminal and run the **standalone release Setup** again. It offers Open Chameleon, Repair, Update and Uninstall. Repair recopies the supplied payload, wrappers/module, missing profile loader, PATH and shortcuts; then verifies Ollama/model/API. Update applies the version bundled with the installer while preserving configuration. No remote update service is included. If files are locked, close installed processes and retry from the external installer.

The installer stages the complete runtime, checks disk space and hashes, retains the old runtime until the manifest commits, and restores prior integration files/PATH/registration if that phase fails. A damaged profile block is detected before replacement. Repair from the installed application displays a responsive preparation window while relocating its loaded libraries.

Child PowerShell processes rebuild their own edition's module path. This addresses the documented PowerShell 7 → Python → Windows PowerShell inheritance problem: [Microsoft PSModulePath documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_psmodulepath?view=powershell-7.6).

## Uninstall

Use Uninstall Chameleon from Start or Installed Apps. It removes only its marked profile block, its PATH entry, its shortcuts, registration, install directory, config/runtime/logs/history. Profile backups are kept beside the original profiles to allow recovery. Existing user content and other PATH entries remain. Model deletion is a separate No-by-default question only for the model recorded as downloaded by Setup. Ollama removal is offered only if Setup installed it, and uses its official uninstaller. Other models are never deleted by Chameleon. Restoring a policy changed by Setup also requires consent.
