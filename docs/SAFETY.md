# Safety

`RiskEngine` never accepts the model's risk label or confidence as permission. Typed query/navigation actions are SAFE after required path checks. Deletion, environment changes and supported mutation commands require confirmation. The default answer is No, including headless runs. Strict mode additionally confirms queries; it cannot disable BLOCKED.

Typed delete paths are resolved before evaluating protected targets, including junction/symlink targets. Drive roots, Windows, System32 and descendants are blocked. For arbitrary generated commands, interpolation hides destructive targets and is blocked on delete operations. Disk formatting, partitioning, nested shells/interpreters, encoded commands, eval, downloads and unknown executable commands are blocked. Compound queries require confirmation. The engine is intentionally conservative: a complex read-only PowerShell pipeline can require confirmation because independently proving arbitrary shell expressions harmless is not possible. Prefer typed actions.

Commands needing administrative capabilities require an already elevated shell; the app never requests UAC or auto-elevates. Privileges are inherited. Any plan requiring admin is blocked as a whole when the token is not elevated. Command failures stop subsequent actions; shell operations are not a filesystem transaction and cannot be rolled back automatically.

The policy applies only to generated AI actions. Direct shell commands remain under user control. This is a local assistant rather than a sandbox: approved commands execute with the user's token. A compromised same-user process can already control the user's shell and is not isolated by this mechanism.
