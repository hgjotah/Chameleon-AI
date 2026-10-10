# Delivery validation · 2026-10-10

Executed on Windows 11 x64 (build 26200), Python 3.13.14, Windows PowerShell 5.1.26100.9444 and PowerShell 7.6.5. Dependencies and npm resources are pinned. Evidence is generated under ignored `artifacts/`; source and distribution files are under Git and `dist/` respectively.

## Passed checks

| Check | Actual result / evidence |
|---|---|
| Ruff | All checks passed |
| mypy | No issues in 41 source files |
| pytest without Ollama | 92 passed, 1 skipped; includes cancellation, real ConPTY and isolated Windows installation |
| Optional Qwen inference | 4 passed in 149.28 seconds; real `qwen3:4b-instruct` |
| Spanish / English model requests | Process RAM query, Python files over 1 MB, PDF modification date and explanation without actions |
| Network boundary | Real inference transport rejects every host except `127.0.0.1`; remote model aliases are rejected before sending prompts |
| CMD parent state | Real wrapper changes cwd, including spaces, Unicode and shell metacharacters; dry-run leaves cwd unchanged; temporary actions removed |
| PowerShell parent state | Real 5.1 and 7.6.5 module invocations preserve cwd in the calling shell |
| Windows installation | Actual registry, ACL and COM shortcuts tested with an isolated HKCU key, temporary APPDATA and profiles; repeated install, Repair and removal pass |
| Profiles / PATH | UTF-8, BOM UTF-8 and UTF-16 exact roundtrip; incomplete blocks stop before replacing the installed payload; unrelated PATH entries preserved |
| GUI CMD | Local xterm renderer, real ConPTY, natural navigation, direct command, Python REPL, resize, Unicode and truecolor screenshots |
| GUI PowerShell | Same navigation/direct command/REPL checks pass |
| GUI actual AI | Qwen produces a validated size filter, the trusted helper runs in the native shell and only the >1 MB Python file is returned |
| Setup worker | Qt installation flow, actual payload copy, preserved temporary profile, actual Qwen probe and removal pass |
| ConPTY applications | Python arithmetic REPL, actual Git/SSH version output, 1,200 lines and ping replies; Ctrl+C returns to the real prompt |
| Cancellation | Cancellation immediately after submission prevents a plan from reaching execution |
| Freeze integrity | 39 packaged Chameleon code objects match the current source exactly |
| Actual executables | 11 checks pass, including real Qwen inference from frozen Core, CMD/PS parent state, Qt/ConPTY, standalone Setup extraction, Settings, Qt scales and removal |
| Ollama actually stopped | Frozen Core fails the complex request safely; the frozen GUI still runs natural local navigation and direct commands. Ollama is restarted and the requested model remains installed |
| Release integrity | Source/portable ZIP CRC checks pass; SHA256 matches all three release files; native OpenConsole host and all documentation are included |

The one skip is the literal exclamation-mark caller scenario with CMD `/v:on`: CMD expands `!` before the wrapper can receive it. Ordinary CMD `/v:off` and PowerShell support the path. This native shell limitation is documented in SHELL_INTEGRATION.md.

## Distribution verification

The complete `scripts/build.ps1 -SkipInstall` run passed lint, types, 92 tests, compilation, bundled integrity checks and all 10 default executable checks. The final standalone installer and portable ZIP are built with PyInstaller. The additional `scripts/frozen_smoke.py --ai` run passed all 11 checks with Python/Node removed from PATH: CLI version, Qwen/schema/safety/size query, persistent parent cwd, offline-model terminal, local renderer, Setup extraction, Settings, simulated Qt scale 1.25/1.5 and removal. Its final results are recorded in `artifacts/frozen/results.json`. `scripts/verify_frozen.py --installer` confirms that Setup embeds the exact final payload. `dist/SHA256SUMS.json` records final release hashes.

Packaging review identified and fixed two genuine distribution errors before delivery: unrelated developer-tool ICU DLLs collected from PATH, and pywinpty's missing dynamically launched OpenConsole host. Build path isolation, explicit host bundling and mandatory frozen GUI smoke prevent recurrence. These checks exercise actual native shell output, not merely creation of a window.

## Environmental limits and manual release checks

These scenarios were **not** represented as passed:

- A clean Windows VM with Internet physically disconnected. The host's network was retained because this Codex session depends on it. Run the offline procedure below before broad public release.
- Authenticated SSH to a remote test host, full-screen third-party editors/TUIs, npm/winget interactive workflows and destructive/admin diskpart scenarios. No remote account or disposable elevated VM was available. Basic SSH version output and native interactive Python are verified.
- Physical Windows 125%/150% scaling, multiple monitors, actual Spanish keyboard hardware, manual selection/clipboard gestures and Ctrl+Break behavior across different console process groups. Qt scale-factor diagnostics are a narrower automated check.
- Windows 10 1809 and a fresh machine without developer runtimes. The final executable test removes Python/Node from PATH, but is still run on this Windows 11 host.
- Commercial Authenticode signing, GitHub-hosted CI execution and publication to an external GitHub repository. Source, local Git history and CI configuration are supplied; a destination remote/certificate was not supplied.

Qwen's speed depends on hardware. On this host inference uses roughly 5 generated tokens/second in the observed CPU run; complex/cold requests may take tens of seconds. Local navigation rules avoid inference. Settings allows increasing the timeout for slower machines. UI language preference is reserved for future translations; Spanish/English natural requests work now.

## Offline procedure in a disposable Windows VM

1. Install the standalone Chameleon release, official Ollama and `qwen3:4b-instruct`. Complete Setup's local inference probe.
2. Keep Ollama running locally and disconnect the VM's external network adapter. Keep loopback enabled.
3. Open a fresh CMD and PowerShell; execute natural navigation and a nontrivial size/date file query. Confirm cwd persists and normal commands remain native.
4. Open Chameleon Terminal; test natural input, Python REPL, colors, resize and clipboard. Verify Qwen inference completes without any download.
5. Close Ollama. Confirm AI OFFLINE while direct commands and local rules continue to work. Run Doctor, then Setup Repair to restart the local backend.
6. Test uninstall and compare the original profiles and PATH with their saved pre-install values.

Use TERMINAL_TEST_MATRIX.md for the remaining interactive/manual scenarios. No claim of complete clean-machine certification is made until these checks are recorded.
