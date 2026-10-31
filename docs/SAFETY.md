# Safety

## Access profiles in 0.5.0

These controls apply to generated actions, not manually typed commands. `RiskEngine`
uses saved application settings, never the model's requested risk/confidence.

| Profile | Effective access |
|---|---|
| Read only | Read/query/navigation; mutation and arbitrary code disabled |
| Balanced (default) | Read/write/delete and known commands; confirm mutations; no arbitrary scripts, downloads or system changes |
| Developer | All effect permissions and arbitrary scripts; confirmation before execution |
| Custom | Individual read/write/delete/command/script/network/system and confirmation switches |
| Full | No Chameleon permission blocks or confirmations; inherited Windows account rights |

Full access does not elevate the process, bypass Windows ACLs/UAC, or make an
unavailable executable exist. Format/protocol validation still rejects malformed
model output. Full mode can perform destructive operations with the user's rights.
Developer and Full profiles intentionally override the conservative allowlist.

Scripts are arbitrary programs: the app cannot prove their filesystem/network
effects from a command string. Custom script access therefore requires all effect
permissions. The controls are **not an OS sandbox**: custom executables, trusted
shell profiles, aliases and installed extensions run with the user's token.
Model/profile changes cancel an active GUI request; an inference uses a settings
snapshot. Application-owned typed creation/copy retain exclusive-create semantics;
raw commands can overwrite where the selected profile permits it.

Command-only generation rejects multiline/prose/fences/JSON, checks suspect cmdlet
availability and validates literal sources for simple read/delete commands before
execution. A known typed source cannot silently change to another existing file.
These checks reduce mistakes; they do not prove arbitrary command semantics.

## Conservative behavior retained for Balanced / structured planning

`RiskEngine` never accepts the model's risk label or confidence as permission. Typed query/navigation actions are SAFE after required path checks. Deletion, environment changes and supported mutation commands require confirmation. The default answer is No, including headless runs. Strict mode additionally confirms queries; it cannot disable BLOCKED.

Typed `create`, `mkdir`, `copy` and `move` operations also require confirmation. The review shows literal source/destination/content instead of an opaque encoded payload. File content is passed as structured data, never interpreted as shell syntax. New files use exclusive creation; existing destinations are refused, including files appearing between approval and execution. Missing parents and invalid Windows names produce a clear error. Protected destinations and moves out of protected system paths are blocked.

Typed delete paths are resolved before evaluating protected targets, including junction/symlink targets. Drive roots, Windows, System32 and descendants are blocked. For arbitrary generated commands, interpolation hides destructive targets and is blocked on delete operations. Disk formatting, partitioning, nested shells/interpreters, encoded commands, eval, downloads and unknown executable commands are blocked. Compound queries require confirmation. The engine is intentionally conservative: a complex read-only PowerShell pipeline can require confirmation because independently proving arbitrary shell expressions harmless is not possible. Prefer typed actions.

Commands needing administrative capabilities require an already elevated shell; the app never requests UAC or auto-elevates. Privileges are inherited. Administrative requirements are derived from actual actions by the risk engine; a model's advisory flag cannot block a normal user-file operation. Actions independently assessed as administrative are blocked as a whole when the token is not elevated. Command failures stop subsequent actions; shell operations are not a filesystem transaction and cannot be rolled back automatically.

The policy applies only to generated AI actions. Direct shell commands remain under user control. This is a local assistant rather than a sandbox: approved commands execute with the user's token. A compromised same-user process can already control the user's shell and is not isolated by this mechanism.
