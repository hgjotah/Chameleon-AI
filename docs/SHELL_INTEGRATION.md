# Shell protocol

## CMD

`bin/chameleon.cmd` calls `ChameleonCore.exe --emit cmd --response <private-file>` directly, without reparsing request arguments inside FOR /F command substitution. The exclusive response file contains only an unpredictable 32-character hex token. FOR /F reads that ASCII file, never a model-generated command. Human messages go to stderr; stdin remains attached for confirmation. Noninteractive mode declines confirmation. Errors produce no token, so the wrapper cannot execute an error message as a command.

The core writes `<token>.cmd` atomically with CREATE_EXCLUSIVE in the per-user private runtime actions directory. Its validated, rendered commands are never model text parsed by the wrapper. The wrapper calls this exact file in the **current CMD interpreter** after ending its own local scope. Action files hide their echo, disable delayed expansion locally, use UTF-8 while running and restore the previous code page. Since ENDLOCAL also restores cwd, the final line exports the resulting cwd and approved environment variables back into the parent. The wrapper deletes the action file **after return**; deleting an executing batch can make CMD lose its input file. A failed action stops the remaining plan. Stale actions and response files are removed after 15 minutes on subsequent invocation. Only the owning user and SYSTEM have runtime access after installation; another process running as that same user is outside the security boundary.

CMD performs its own expansion **before** invoking any program: unquoted `&`, `%VAR%`, and `!VAR!` with `/v:on` have CMD's usual meaning. Quote natural-language paths. For literal exclamation marks use ordinary CMD `/v:off`, the default, or PowerShell. Paths passed from batch scripts must use batch quoting/escaping for the calling script as usual. Characters `"`, `<`, `>`, `|`, NUL and control characters are not valid Windows filename components; rejected rather than silently modified. Core rendering doubles percent signs for batch data and quotes valid path metacharacters. Wrapper invocation from another batch requires `call chameleon ...` as with any `.cmd`.

## PowerShell

The profile imports `bin/Chameleon.psm1`. `chameleon` accepts all remaining arguments as a string array, passes the actual `$PID` and `(Get-Location).Path` and reads one validated JSON Plan. Typed operations execute with `-LiteralPath`, avoiding wildcard/eval injection. Environment changes target Process scope. Only approved `command` actions create a ScriptBlock. Encoding is restored after the invocation. The function changes the real shell's location and process environment.

## GUI shell

Only the child CMD's environment PROMPT or child PowerShell's prompt function is customized. A random authenticated OSC title carries cwd and prompt completion. It is consumed invisibly by xterm; no global user prompt modification occurs. Child PowerShell exports aliases/functions and version into a private random session file removed on close. Without a prompt marker, input is raw. See ARCHITECTURE.md for line editing and interactive programs.
