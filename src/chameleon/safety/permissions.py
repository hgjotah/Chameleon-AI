"""Command permission checks, separate from untrusted model output.

This is an application policy, not an OS sandbox. Arbitrary scripts require all
effect permissions: their filesystem/network effects cannot be inferred safely.
"""

import re

from chameleon.core.config import SafetyConfig
from chameleon.core.schemas import Action

READ_COMMANDS = {
    "dir",
    "cd",
    "chdir",
    "cls",
    "type",
    "echo",
    "pwd",
    "ls",
    "cat",
    "whoami",
    "hostname",
    "ver",
    "tasklist",
    "get-childitem",
    "get-content",
    "get-location",
    "get-process",
    "get-date",
    "get-service",
    "measure-object",
    "select-object",
    "sort-object",
    "where-object",
    "test-path",
    "get-item",
    "get-computerinfo",
    "get-ciminstance",
    "get-wmiobject",
    "get-host",
    "get-psdrive",
    "get-volume",
    "get-disk",
    "get-itemproperty",
    "set-location",
    "clear-host",
    "push-location",
    "pop-location",
    "pushd",
    "popd",
    "sl",
    "gci",
    "gc",
    "gi",
    "gps",
    "ps",
    "gl",
}


def session_change(command: str) -> bool:
    """Narrow, literal console-only changes; no filesystem/system elevation."""
    if re.fullmatch(r"\s*color(?:\s+[0-9a-fA-F]{1,2})?\s*", command, re.I):
        return True
    if re.fullmatch(r"\s*title\s+[^\r\n&|<>^%!]+", command, re.I):
        return True
    if re.fullmatch(
        r"\s*\$Host\.UI\.RawUI\.(?:ForegroundColor|BackgroundColor)\s*=\s*\[(?:System\.)?ConsoleColor\]::[A-Za-z]+\s*",
        command,
        re.I,
    ):
        return True
    return bool(
        re.fullmatch(
            r"\s*\$Host\.UI\.RawUI\.(?:ForegroundColor|BackgroundColor|WindowTitle)\s*=\s*(?:'[^'\r\n]*'|\"[^\"$`\r\n]*\")\s*",
            command,
            re.I,
        )
    )


def session_read(command: str) -> bool:
    # Bare variables/properties print data; their values are not evaluated as code.
    return bool(
        re.fullmatch(
            r"\s*(?:\$env:[A-Za-z_][A-Za-z0-9_]*|\$(?:PWD(?:\.Path)?|PSVersionTable(?:\.[A-Za-z]+)?|Host(?:\.[A-Za-z]+){0,3}))\s*",
            command,
            re.I,
        )
    )


def denied(action: Action, policy: SafetyConfig) -> str | None:
    if policy.mode == "full":
        return None
    caps = policy.permissions()
    if action.kind == "command" and session_read(action.command):
        return None if caps["read"] else "Permisos desactivados: read. Ajustes → Acceso del modelo."
    if action.kind == "command" and session_change(action.command):
        return (
            None
            if caps["commands"]
            else "Permisos desactivados: commands. Ajustes → Acceso del modelo."
        )
    needed = {"read"}
    if action.kind in ("create", "mkdir", "copy", "move", "env"):
        needed = {"write"}
    elif action.kind == "delete":
        needed = {"delete"}
    elif action.kind == "command":
        command = action.command
        needed = set()
        # Executable invocations and effects anywhere in a compound command.
        words = {
            s.casefold().removesuffix(".exe") for s in re.findall(r"[\w-]+(?:\.exe)?", command)
        }
        first = re.match(r"\s*(?:&\s*)?[\"']?([^\s\"']+)", command)
        executable = (
            first[1].replace("\\", "/").rsplit("/", 1)[-1].casefold().removesuffix(".exe")
            if first
            else ""
        )
        if executable in READ_COMMANDS:
            needed.add("read")
        heads = set()
        for segment in re.split(r"&&|\|\||[&;|]", command):
            invocation = re.match(r'\s*["\x27]?([^\s"\x27]+)', segment)
            if invocation:
                heads.add(
                    invocation[1]
                    .replace("\\", "/")
                    .rsplit("/", 1)[-1]
                    .casefold()
                    .removesuffix(".exe")
                )
        script = (
            bool(
                heads
                & {
                    "python",
                    "python3",
                    "node",
                    "pwsh",
                    "powershell",
                    "cmd",
                    "wscript",
                    "cscript",
                    "mshta",
                    "rundll32",
                    "invoke-expression",
                    "iex",
                    "invoke-command",
                    "start-process",
                    "call",
                }
            )
            or bool(re.search(r"\.(?:ps1|py|pyw|js|vbs|bat|cmd)$", executable, re.I))
            or bool(re.search(r"-(?:enc|encodedcommand)\b", command, re.I))
        )
        if script or re.search(r"\$\(|`|%[^%]+%|![^!]+!|[{}]|::|\.\w+\s*\(", command):
            needed = {"commands", "scripts", "read", "write", "delete", "network", "system"}
        else:
            if words & {
                "del",
                "erase",
                "rd",
                "rmdir",
                "rm",
                "remove-item",
                "deltree",
                "remove-itemproperty",
            }:
                needed.add("delete")
            if words & {
                "copy",
                "move",
                "ren",
                "rename",
                "mkdir",
                "md",
                "new-item",
                "set-content",
                "add-content",
                "out-file",
                "set-itemproperty",
                "set-acl",
                "set",
                "cp",
                "mv",
                "ni",
                "sc",
                "tee-object",
            } or re.search(r"(?<![<])>{1,2}", command):
                needed.add("write")
            if words & {
                "curl",
                "wget",
                "invoke-webrequest",
                "invoke-restmethod",
                "iwr",
                "irm",
                "ssh",
                "scp",
                "sftp",
                "winget",
                "pip",
                "npm",
                "ping",
            } or re.search(r"https?://|\\\\|\bgit\s+(?:clone|fetch|pull|push)\b", command, re.I):
                needed.add("network")
            if (
                words
                & {
                    "reg",
                    "netsh",
                    "bcdedit",
                    "format",
                    "diskpart",
                    "clear-disk",
                    "format-volume",
                    "remove-partition",
                    "stop-service",
                    "set-service",
                    "restart-service",
                    "shutdown",
                    "restart-computer",
                    "stop-computer",
                    "takeown",
                    "icacls",
                    "set-executionpolicy",
                }
                or needed & {"write", "delete"}
                and re.search(
                    r"\b(?:windows|hklm|hkey_local_machine|system32|syswow64)\b|[a-z]:[\\/](?:[\"'\s]|$)",
                    command,
                    re.I,
                )
            ):
                needed.add("system")
            if executable not in READ_COMMANDS:
                needed.add("commands")
            # Unknown programs can hide arbitrary code/effects. They are scripts
            # for permission purposes, even when the executable has another name.
            known_mutations = {
                "del",
                "erase",
                "rd",
                "rmdir",
                "rm",
                "remove-item",
                "copy",
                "move",
                "ren",
                "rename",
                "mkdir",
                "md",
                "new-item",
                "set-content",
                "add-content",
                "out-file",
                "set",
                "cp",
                "mv",
                "ni",
                "git",
                "curl",
                "wget",
                "ping",
                "ipconfig",
                "taskkill",
                "stop-process",
                "reg",
                "netsh",
                "sc",
                "shutdown",
                "winget",
                "icacls",
                "takeown",
            }
            if executable not in READ_COMMANDS | known_mutations:
                needed.update({"scripts", "write", "delete", "network", "system"})
            for segment in re.split(r"&&|\|\||[&;|]", command):
                match = re.match(r"\s*[\"']?([^\s\"']+)", segment)
                program = (
                    match[1].replace("\\", "/").rsplit("/", 1)[-1].casefold().removesuffix(".exe")
                    if match
                    else ""
                )
                if program and program not in READ_COMMANDS | known_mutations:
                    needed.update({"commands", "scripts", "write", "delete", "network", "system"})
            if words & {"curl", "wget"} and re.search(
                r"\s(?:-o|-O|--output|--remote-name)\b", command
            ):
                needed.add("write")
    missing = sorted(name for name in needed if not caps[name])
    return (
        "Permisos desactivados: " + ", ".join(missing) + ". Ajustes → Acceso del modelo."
        if missing
        else None
    )
