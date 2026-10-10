# Terminal test matrix

Record actual machine/shell/version and evidence. Automated tests cover the basic ConPTY path; interactive network/admin applications require appropriate resources and token.

| Scenario | Procedure | Evidence / expected result |
|---|---|---|
| CMD builtins | dir, cd, set, echo, cls | External parent cwd pytest; GUI echo smoke |
| PowerShell 5.1 | Set-Location, Get-ChildItem; aliases | External cwd pytest; GUI smoke |
| PowerShell 7 | same, if installed | Actual 7.6.5 parent-cwd test passed; conditionally skips absent shell |
| Python REPL | print, edit line, exit | ConPTY and GUI automated smoke |
| Git | git status/log --color | Direct classification and actual `git --version` in ConPTY; color/status interactive inspection remains manual |
| SSH | ssh -V; connect to a test host and type | Actual `ssh -V` in ConPTY passed; authenticated remote session requires test host |
| ping / Ctrl+C | ping -t 127.0.0.1 then interrupt | ConPTY automated smoke |
| Ctrl+Break | Ctrl+Pause while appropriate process runs | Check Windows host permits control event; fallback Ctrl+C |
| ANSI | 16/256/truecolor escapes | xterm renderer; GUI screenshot truecolor |
| Resize / wrapping | resize while output and REPL active | ConPTY resize + GUI smoke |
| Unicode / Spanish keyboard | ñ, áéíóú, ¿¡, spaces in paths | Quoting/cwd tests + screenshot |
| Large output | 1200 lines through the real shell | Automated ConPTY test received final line; visual scrolling inspection remains manual |
| Interactive input | python, node, ssh, editor | Marker inactive; raw input until shell prompt returns |
| Tab / arrows / history | edit known command using shell keys | Native shell editing; visual manual check |
| Selection / paste | mouse select; Ctrl+Shift+C/V, multiline paste | xterm; multiline bypasses AI |
| AI unavailable | stop local Ollama, launch app | Direct command and local rule still usable; AI OFFLINE |
| Offline | disable external networking in a disposable VM, keep loopback | local rules + cached Qwen inference + renderer; no download |
| Admin tools | elevated launch, diskpart interactive in disposable VM | Inherited token; never run destructive actions on host |
| High DPI | 125% / 150% scale and multi-monitor | Frozen diagnostic uses Qt scale 1.25/1.5; physical Windows scaling and multi-monitor remain manual |

Never disconnect the host network or modify its partitions merely for automated testing. Use a disposable Windows VM for destructive/admin/network isolation checks. See VALIDATION.md for what was actually executed in this delivery.
