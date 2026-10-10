# Delivery validation · 0.2.0 · 2026-10-10

Executed on Windows 11 x64 (build 26200), Python 3.13.14, Windows PowerShell 5.1.26100.9444 and PowerShell 7.6.5. Dependencies and npm resources are pinned, including pywinpty 3.0.5 with its event-driven ConPTY teardown fix ([official release notes](https://github.com/andfoy/pywinpty/releases/tag/v3.0.5)). Evidence is generated under ignored `artifacts/`; source and distribution files are under Git and `dist/` respectively.

## Passed checks

| Check | Actual result / evidence |
|---|---|
| Ruff | All checks passed |
| mypy | No issues in 45 source files |
| pytest without Ollama | 118 passed, 1 skipped in the full suite on pywinpty 3.0.5; 23 focused regression tests then passed, including three newly added tests for ConPTY exit, conflicting destinations and GUI error recovery (121 distinct tests verified). Includes literal file operations, cancellation, native wrappers, real ConPTY, rollback and isolated Windows installation |
| Optional Qwen inference | 4 passed in 218.23 seconds; real `qwen3:4b-instruct`, with other QA work running concurrently |
| Spanish / English model requests | Process RAM query, Python files over 1 MB, PDF modification date and explanation without actions |
| Network boundary | Real inference transport rejects every host except `127.0.0.1`; remote model aliases are rejected before sending prompts |
| Literal creation | Actual GUI confirmation refused/accepted with Unicode names and shell symbols in content; real interactive CMD, Windows PowerShell and PowerShell 7 wrappers create the exact requested file; both PowerShell versions also read its UTF-8 accents correctly |
| PowerShell module environment | Real Windows PowerShell successfully loads Security modules from a PowerShell 7 parent; incompatible inherited module paths are removed |
| Installation rollback | Injected final-manifest failure restores the previous runtime, module, profile and manifest |
| Settings shell change | Existing sessions retain their actual shell while new-session preference changes |
| Local creation latency | 100 plan-only iterations average 4.705 ms; no file writes and no model inference in this benchmark |
| Minimal model probe | Structured local probe completed in 11.25 seconds including model startup |
| CMD parent state | Real wrapper changes cwd, including spaces, Unicode and shell metacharacters; dry-run leaves cwd unchanged; temporary actions removed |
| PowerShell parent state | Real 5.1 and 7.6.5 module invocations preserve cwd in the calling shell |
| Windows installation | Actual registry, ACL and COM shortcuts tested with an isolated HKCU key, temporary APPDATA and profiles; repeated install, Repair and removal pass |
| User installation updated | Actual `%LOCALAPPDATA%\ChameleonAI` updated to 0.2.0 from an independently frozen verification process, retaining preferences, profile content and unrelated PATH entries. Installed Doctor reports all checks OK; interactive CMD, PowerShell 5.1 and PowerShell 7 create literal UTF-8 files after confirmation (`artifacts/installed-update.json`) |
| Profiles / PATH | UTF-8, BOM UTF-8 and UTF-16 exact roundtrip; incomplete blocks stop before replacing the installed payload; unrelated PATH entries preserved |
| GUI CMD | Local xterm renderer, real ConPTY, long wrapped paths, navigation, direct command, Python REPL, rapid Enter, Unicode and truecolor screenshots |
| GUI PowerShell | Same navigation/direct command/REPL checks pass; rapid Enter captures full Unicode content, and replayed ConPTY titles cannot enable AI inside a REPL |
| GUI actual AI | Qwen produces a validated size filter, the trusted helper runs in the native shell and only the >1 MB Python file is returned |
| Setup worker | Qt installation flow, actual payload copy, preserved temporary profile, actual Qwen probe and removal pass |
| ConPTY applications | Python arithmetic REPL, actual Git/SSH version output, 1,200 lines and ping replies; Ctrl+C returns to the real prompt |
| GUI preparation errors | Oversized CMD content reports its actual error, releases busy input and leaves the filesystem unchanged |
| Conflicting file destinations | Create operations reject destination fields that could disagree with the reviewed path |
| ConPTY exit regression | Closing after the native shell has already exited releases the blocked reader; both actual ConPTY tests pass |
| Cancellation | Cancellation immediately after submission prevents a plan from reaching execution |
| Freeze integrity | 43 packaged Chameleon code modules and every interface/shell asset match the current source exactly; embedded payload assets are checked too |
| Actual executables | 10 standard frozen checks pass plus a separate final frozen-Core Qwen check: real structured inference, CMD/PS parent state, Qt/ConPTY, standalone Setup extraction, Settings, Qt scales and removal |
| Ollama actually stopped | Frozen Core fails the complex request safely; the frozen GUI still runs natural local navigation and direct commands. Ollama is restarted and the requested model remains installed |
| Release integrity | Source/portable ZIP CRC checks pass; SHA256 matches all three release files; native OpenConsole host and all documentation are included |

The one skip is the literal exclamation-mark caller scenario with CMD `/v:on`: CMD expands `!` before the wrapper can receive it. Ordinary CMD `/v:off` and PowerShell support the path. This native shell limitation is documented in SHELL_INTEGRATION.md.

## Distribution verification

The 0.2.0 build uses `scripts/build.ps1 -SkipInstall -SkipTests` after separately passing lint, type checking, 121 distinct non-model tests and all four actual model tests. The build itself checks packaged source integrity, embedded installer payload integrity and real executable smoke tests. The smoke now creates a file through an actual confirmation dialog in CMD and PowerShell and verifies its literal content, also at Qt scale factors 1.25/1.5. Final evidence is recorded in `artifacts/frozen/results.json` and `artifacts/frozen/ai-result.json`; release hashes are in `dist/SHA256SUMS.json`.

Verification on the actual account uncovered Microsoft Store Python's AppData/HKCU redirection during source-driven installation. An independently frozen process completed and checked the actual installation instead. `scripts/run.ps1 setup` now uses the built standalone installer; this prevents the source launcher from creating an installation invisible to native CMD/PowerShell. See BUILDING.md for the upstream explanation.

The 0.1.0 executable checks also established safe failure while the actual Ollama service was stopped, and direct terminal/navigation operation while offline. 0.2.0 retains those boundaries and adds local file creation/copy/move. Automated tests cover explicit offline/failed-probe outcomes separately from successful terminal installation.

Packaging review identified and fixed two genuine distribution errors before delivery: unrelated developer-tool ICU DLLs collected from PATH, and pywinpty's missing dynamically launched OpenConsole host. Build path isolation, explicit host bundling and mandatory frozen GUI smoke prevent recurrence. These checks exercise actual native shell output, not merely creation of a window.

## Environmental limits and manual release checks

These scenarios were **not** represented as passed:

- A clean Windows VM with Internet physically disconnected. The host's network was retained because this Codex session depends on it. Run the offline procedure below before broad public release.
- Authenticated SSH to a remote test host, full-screen third-party editors/TUIs, npm/winget interactive workflows and destructive/admin diskpart scenarios. No remote account or disposable elevated VM was available. Basic SSH version output and native interactive Python are verified.
- Physical Windows 125%/150% scaling, multiple monitors, actual Spanish keyboard hardware, manual selection/clipboard gestures and Ctrl+Break behavior across different console process groups. Qt scale-factor diagnostics are a narrower automated check.
- Windows 10 1809 and a fresh machine without developer runtimes. The final executable test removes Python/Node from PATH, but is still run on this Windows 11 host.
- Commercial Authenticode signing, GitHub-hosted CI execution and publication to an external GitHub repository. Source, local Git history and CI configuration are supplied; a destination remote/certificate was not supplied.

Qwen's speed depends on hardware. On this host inference uses roughly 5 generated tokens/second in the observed CPU run; complex/cold requests may take tens of seconds. Concrete creation, folder, read, copy, move, navigation and common process requests avoid inference. Complex model requests still depend on CPU and available RAM; no universal response-time guarantee is made. Settings allows increasing the timeout for slower machines. UI language preference is reserved for future translations; Spanish/English natural requests work now.

## Offline procedure in a disposable Windows VM

1. Install the standalone Chameleon release, official Ollama and `qwen3:4b-instruct`. Complete Setup's local inference probe.
2. Keep Ollama running locally and disconnect the VM's external network adapter. Keep loopback enabled.
3. Open a fresh CMD and PowerShell; execute natural navigation and a nontrivial size/date file query. Confirm cwd persists and normal commands remain native.
4. Open Chameleon Terminal; test natural input, Python REPL, colors, resize and clipboard. Verify Qwen inference completes without any download.
5. Close Ollama. Confirm AI OFFLINE while direct commands and local rules continue to work. Run Doctor, then Setup Repair to restart the local backend.
6. Test uninstall and compare the original profiles and PATH with their saved pre-install values.

Use TERMINAL_TEST_MATRIX.md for the remaining interactive/manual scenarios. No claim of complete clean-machine certification is made until these checks are recorded.
