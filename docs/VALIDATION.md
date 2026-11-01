# Delivery validation · 0.5.1 · 2026-11-01

## Current release · 0.5.1

Ruff passed and mypy checked 56 source files. The final non-model suite passed
**219 tests**, with one documented CMD delayed-expansion skip. New checks cover
native AST parsing/static binding, unknown parameters and pipeline commands,
read-only inspection without executing a proposed write, literal session reads,
console permissions, caller metadata boundaries, ambiguous names, preserved
source/destination operands, CMD arity, code delimiters and native cmdlet routing.

The command prompt contains no task/answer examples. Native references and live
session property types are discovered from the actual OS. The model still chooses
the command. Corrections and independent policy checks occur before execution.
Two intermediate 32-case forced-model matrices exposed wrong cmdlets, incorrect
arguments, lost quotes and semantic failures; these were exploratory, NOT a claim
that every model translation passed. Their findings drove the independent checks.

Final real ConPTY runs verified the requested green text effect in all four
model/shell combinations under the Full profile: qwen2.5:0.5b and
qwen3:4b-instruct, CMD and Windows PowerShell. The command was chosen by the model,
not supplied as a task/answer example. QA whitelisted the proposed effect before
executing it and observed ANSI color output or actual ForegroundColor afterwards.
Final evidence: `artifacts/console-precision051-tiny.json` and
`artifacts/console-precision051-large.json`. Earlier Balanced/Full exploratory
runs are retained separately; they are not substituted for the final runs.

Small-model discovery uses the actual parameter count from local model metadata.
It starts with a compact context and expands runtime facts during native review.
Native help-derived value validation also covers inline CMD argument separators;
invalid documented values cannot bypass review by appearing as a single word.
Truncated responses are rejected and can receive a bounded corrective retry.

All 54 bundled Chameleon modules match the final source, with exact interface,
shell assets, embedded payload and logo verification. Ten frozen executable checks
pass, including CMD/PS parent state, Qt/xterm/ConPTY, Setup/Settings, missing AI,
DPI 1.25/1.5 and removal preserving the original profile. The standalone release
was built with clean PyInstaller caches; stale incremental builds were rejected.

The real account is updated to 0.5.1. Installed native wrappers created, read,
copied and deleted a hidden-extension file in CMD, PowerShell 5.1 and PowerShell 7;
literal Unicode content containing an ampersand was preserved. Doctor passed all
12 checks. A final installed frozen-Core forced-model dry-run returned COLOR 2
from actual qwen2.5:0.5b inference (2 calls, 10 tokens, 14.4 s on this run).
Configuration (including the selected model/profile), user PATH and PowerShell
profile bytes are unchanged. The installed Core SHA256 equals the release Core.
Evidence: `artifacts/installed-native051.log`, `doctor051.log`,
`installed-qwen051.log`, `actual_account_after051.json`, `build051-release.log`.

These checks do not establish universal semantic correctness. The 0.5B model still
misunderstands some tasks; a valid command name/AST alone cannot prove intent.
The Full profile retains arbitrary access with the Windows user's privileges.
Simple local operations remain available without inference. Extra reference
review adds latency on this CPU; validated simple tasks avoid a redundant round.
Source/portable ZIP CRC and SHA256 verification also pass for the final delivery.


## Previous release · 0.5.0

Ruff passed and mypy passed 54 source files. The complete non-model suite passed:
**198 passed, 1 skipped, 4 deselected**. This includes profile
permission matrices, read-only mutation/script checks, arbitrary full-access
assessment, independent delete/network/write switches, script effect requirements,
command-only format/retry, wrong-existing-source correction, literal CMD environment
export, real CMD FOR/script execution and app-authored policy handoff to helpers.
Explicit requests to execute an existing script use a direct verified invocation;
forced model translation receives that invocation and rejects replacement code or
extra interpreter wrappers. Missing scripts fail before execution.
The model cannot inject a Full policy through its JSON plan: the engine overwrites
the execution policy snapshot with the user's chosen configuration.

Twelve actual local inference cases passed, without changing model tags: each of
qwen2.5:0.5b and qwen3:4b-instruct generated hostname, directory creation and literal
file deletion commands for CMD and PowerShell. All replies were plain single-line
commands. Proposals were assessed but the model-generated delete cases were not
executed. Observed qwen2.5 times were 1.202–2.744 s; qwen3 times were 4.909–9.608 s.
These are host/run measurements, not universal latency or semantic guarantees.
Evidence: `artifacts/models05-real.json`. Initial tests caught invented cmdlets,
JSON-escaped Windows paths and a misspelled temporary directory; command discovery,
literal context, relative-source instructions and source validation were added.

Both source GUI scenarios passed eight real Qt/xterm/ConPTY checks each, including
normal commands, persistent cwd, native REPL, literal Unicode content and declined/
accepted creation. A separate native settings test verified Full's effective
permissions/no confirmation, editable Custom controls, selected-model persistence
and runtime profile switching. It used an isolated QA home.

The Liquid Glass renderer reuses complete MIT PyGlass modules at revision
`c12d91f1526badbe18f619ff893d2cdbbd86dac5`, adapted to PySide6. License and provenance
are bundled. Refraction reads only app-painted pixels and caches bounded kernels;
no desktop capture modules are imported. Source screenshots are in ignored
`artifacts/preview03/` (directory name retained from the existing capture helper).

Final frozen verification passed all **52 bundled modules**, exact source assets,
embedded payload/logo checks and ten executable smoke scenarios including Qt,
Setup/Settings, CMD/PowerShell, DPI 1.25/1.5 and a missing model. The full NumPy
wheel license hierarchy is retained, including its 45,831-byte main/bundled notice;
license files with equal basenames no longer overwrite each other.

The real account is updated to 0.5.0. Doctor passed all 12 checks in the verification
environment. An independently frozen controller verified installed creation and
confirmed hidden-extension deletion in CMD, Windows PowerShell and PowerShell 7.
Both installed GUI scenarios passed actual qwen2.5 command-only file reads, native
file output, confirmed literal creation and a normal command after the response.
Full-access CLI tests invoked existing CMD and PowerShell scripts using the actual
qwen2.5 model with noninteractive confirmation disabled; both emitted the expected
QA marker. These tests used isolated data homes and harmless scripts only.

The physical installed Core equals the distribution Core by SHA256. Existing
preference values, exact profile bytes and the user PATH are preserved; new settings
default to Balanced and command-only. Evidence is in `artifacts/build05-final.log`,
`artifacts/installed-update05.log`, `artifacts/scripts05-native.log`,
`artifacts/installed-native05.log`, `artifacts/frozen-ai05/` and native before/after
receipts. No destructive Full-access disk/system command is executed during QA;
such strings are assessment-only tests. A clean Windows VM remains untested.

## Historical release · 0.4.0 · 2026-10-11

## Current release · 0.4.0

Native PowerShell checks found official Ollama 0.40.2 (valid Ollama Inc. Authenticode signature) and downloaded `qwen3:4b-instruct` in this account. Its digest is `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`, Qwen3 4B Instruct Q4_K_M. This host uses CPU inference (i5-12450H, 16 GB RAM); free RAM during the run was below 1 GB. Presence, API availability and actual generation are separate checks.

| Real model case, sequential run without concurrent builds | Result |
|---|---|
| Summarize named file and report actual counter 713 | 10.092 s, one call, 24 output tokens, one actual read |
| Forced Qwen creation of saludo.txt containing Hola mundo | 21.478 s, one typed create, confirmation required |
| Forced Qwen delete of Downloads/Prueba with hidden .txt extension | 26.445 s, exact existing file selected, confirmation required; file untouched during planning |
| Explain environment variable | 13.863 s, one concise explanation, no actions |

The previous implementation took 76.3 s for the equivalent summary in a sequential run. The revised implementation reads an unambiguous named summary target before inference, reduces prompts, constrains simple typed actions and streams progress. No timeout increase was used: these checks used the default 90 seconds. Measurements are specific to this host; CPU, memory pressure, cold loading and request size affect latency. Complex queries can remain slower.

Ruff and mypy (46 source files) passed. The final complete non-model suite passed: **156 passed, 1 skipped, 4 deselected in 44.54 s**, including the query-loop and generic inspection-phase regressions. Both source GUI scenarios also passed eight checks each (CMD and PowerShell), including native REPL input and declined/accepted literal file creation. Four additional real Ollama tests passed in 107.56 s: RAM process query, Python files larger than 1 MB, PDF files modified since a date and an explanation. The initial real-query run exposed `inspect` being returned for direct listing/search requests; their grammar now requires native query execution. Any other typed inspection also enters the observation/answer phase after tools run, preventing repeated inspections for wording outside the initial heuristic.

Coverage includes incomplete/error streams, automatic startup of an installed offline backend, typed creation without an invented command, fresh dependency orchestration (install → start → pull → probe), absent binary after installer exit, and silent-install consent flags with an IA-pending exit code. The fresh-machine external install branch is mocked; this account already has the real dependencies and reuses them.

The new supplied PNG is copied byte for byte, SHA256 `46142cbe7368d81869b931af59da66db526125c2d9410d82360132a7ad34a17f`. ICO sizes are generated from it. Setup percentages represent actual downloads; the component row reports binary/server/model state. Options scroll on smaller screens while install/settings buttons remain visible.

The frozen build passed all 44 module comparisons, exact UI/assets comparisons and standalone embedded payload/logo integrity checks. Ten frozen smoke checks passed, including native shell cwd, Qt/xterm/ConPTY, a missing model, Setup/Settings startup, scale factors 1.25/1.5 and preserved profiles after removal. The real account was then updated through the standalone Core with dependency preparation enabled; it reused official Ollama/Qwen and completed actual structured inference. Doctor reported all 12 checks OK in the verification environment.

An independently frozen controller verified actual installed creation and confirmed hidden-extension deletion in CMD, Windows PowerShell and PowerShell 7. The physical installed Core equals the built Core by SHA256. Original preference values and exact profile bytes were preserved; the new CPU-thread option defaults to 4. The first update retained the exact user PATH. The final snapshot showed an unrelated FFmpeg path update from 9.0 to 9.0.2 and a trailing separator; that current PATH was retained, with the Chameleon entry present. Physical installed PNG and shortcut ICO match the source. Normal shells report 0.4.0. CMD was also checked with a refreshed environment: children of an application opened before installation retain its old process PATH until that host restarts.

Evidence: `artifacts/build04-final.log`, `artifacts/performance04-real.json`, `artifacts/installed-update04.log`, `artifacts/installed-native04.log`, `artifacts/doctor04.log`, and before/after native-account snapshots. Installed GUI checks use dedicated QA homes, default 90-second AI timeout, actual Qwen file summaries, confirmed file creation and a native command after the response. Release packages and hashes are under `dist/`.

Both installed CMD and PowerShell GUI checks passed with actual file summaries and native input after the reply. A test launched with `Start-Process -WindowStyle Hidden` timed out before the renderer/session started; normal GUI launch passed. Qt also reported late object registration. The final startup registers the bridge before loading the JS client and reads PTY output only after `Bridge.ready()`, removing the initial reload in accordance with [Qt's registration requirement](https://doc.qt.io/qt-6/qwebchannel.html#registerObject).

## Previous release · 0.3.0

The current release is verified on this Windows 11 x64 host. Evidence is generated in ignored `artifacts/`; packages are in `dist/`. The detailed 0.2.0 baseline below is retained and explicitly identified as earlier validation.

| Current check | Observed result |
|---|---|
| Ruff / mypy | All checks pass; 46 source files type-check |
| Full non-model suite | 137 passed, 1 skipped, 4 model tests deselected in 140.24 seconds, with other QA running |
| Final focused regressions | 84 passed, including UTF-16, hidden extensions, literal paths containing Spanish prepositions, native confirmed deletion and two CLI update checks. 143 distinct non-model tests verified across full/focused runs |
| Reported deletion | Seven Spanish/English variants resolve actual temporary `Prueba.txt`; omitted extensions work for one exact stem, ambiguous candidates require clarification |
| Known folder prefixes | `Downloads/Prueba.txt`, `Descargas\Prueba` and redirected Downloads resolve to actual known-directory locations |
| Native confirmation | CMD, PowerShell 5.1 and PowerShell 7 create a literal Unicode file after confirmation, then delete that temporary file using the folder-before-name phrase with the extension omitted |
| Qwen identity | Real local metadata reports Qwen3-4B-Instruct-2507 / Q4_K_M; observed inference accepts only `127.0.0.1`; no substituted model |
| Forced-Qwen deletion | One actual chat call, 107 output tokens, 67.14 seconds under QA load; correct temporary Downloads path, CONFIRM and file retained (`artifacts/qwen03-real.json`) |
| Grounded actual answer | Qwen requests a typed read, Engine reads actual `registro.txt`, Qwen answers with counter **713**; two calls, 80 output tokens, 51.20 seconds, one inspection and no writes |
| Grounding regression checks | Fabricated file-state answer rejected, writes/out-of-scope inspection rejected, partial listings/secrets tested, UTF-16 BOM and hidden-extension read verified |
| Source GUI | Eight actual Qt/xterm/ConPTY checks each in CMD and PowerShell, including native prompt, navigation, REPL isolation and declined/confirmed literal creation |
| Supplied logo | Project PNG is byte-identical to the user's attachment; SHA256 `e8485698940521545fba7d71e0943212bd741fc7c698e45290a22f2a293e78c9`. ICO sizes derive from this image; preview screenshots display it |
| Final installer regression | 14 focused installer/service/CLI tests pass after moving runtime ACL setup before staging/backup; actual account update then completes with all Doctor checks OK |
| Frozen distribution | 44 packaged code modules and every asset match source; embedded payload and supplied bootstrap PNG match exactly; all 10 frozen executable/renderer/installer checks pass |
| Frozen Core Qwen | Actual read-and-answer returns counter 713 with two model calls and one inspection; 111 tokens / 115.3 seconds during concurrent build, with the isolated QA timeout raised to 180 seconds (`artifacts/frozen-grounding03.json`) |
| Actual user update | 0.3.0 installed; all original preferences, profile bytes and user PATH preserved; installed PNG/ICO match source; Start Menu shortcuts use the new icon. Independently frozen native QA confirms creation and hidden-extension deletion in CMD, PowerShell 5.1 and PowerShell 7 (`artifacts/installed-update03.json`) |

The initial grounded run exposed repeated reads and verbose inspection summaries. The answer phase now closes the tool round explicitly, and the inspection summary is fixed and short. The same actual read-and-answer case dropped from 369 tokens / 188 seconds to 80 tokens / 51 seconds in the observed CPU runs. These are host measurements, not universal response-time guarantees. Default concrete local operations avoid inference; forced Qwen remains slower on CPU. Ctrl+C cancels a pending request.

Current distribution evidence is recorded in `artifacts/build03-final.log`, `artifacts/frozen/results.json` and `artifacts/installed-update03.json`; release hashes are in `dist/SHA256SUMS.json`. The build requires source/asset integrity, exact embedded payload/logo checks and actual executable smoke checks before packaging. Qt Essentials lacks an SVG image plugin, so the checkbox glyph uses PNG; the supplied logo remains untouched.

## Earlier validation · 0.2.0 · 2026-10-10

The actual update exposed an ACL timeout caused by applying inheritable permissions after adding the full runtime backup. The previous installation was recovered with unchanged profiles/PATH. The final installer secures the small actions/session tree before adding staging or backup, bounds ACL setup at 60 seconds and reports a specific timeout error. The subsequent actual update completed.

Actual-account QA must use a native frozen process: Microsoft Store Python can expose an older redirected runtime when launching child shells against AppData. A source-driven QA attempt encountered that older copy; the original configuration was recovered and all checks were repeated from an independently frozen controller. Normal fresh CMD and both PowerShell versions report the installed 0.3.0. The old private cache copy is preserved as a recovery backup; it is not distributed.

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
