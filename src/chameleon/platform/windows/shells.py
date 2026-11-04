import base64
import re
import sys
from pathlib import Path

from chameleon.core.schemas import Action
from chameleon.platform.base import ShellAdapter


def query_command(action: Action, powershell: bool = False, policy_token: str = "") -> str:
    encoded = base64.b64encode(action.model_dump_json().encode("utf-8")).decode("ascii")
    quote = ps_quote if powershell else cmd_quote
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).with_name("ChameleonCore.exe")
        command = quote(str(executable))
    else:
        command = quote(sys.executable) + " -m chameleon"
    operation = "apply" if action.kind in ("create", "mkdir", "copy", "move") else "query"
    result = ("& " if powershell else "") + command + " " + operation + " --encoded " + encoded
    if policy_token:
        result += " --policy " + quote(policy_token)
    if not powershell and len(result) > 7900:
        raise ValueError(
            "The action exceeds CMD's maximum length. Shorten the content or use a PowerShell session."
        )
    return result + (
        "; if ($LASTEXITCODE -ne 0) { throw 'Chameleon: could not complete the action' }"
        if powershell
        else ""
    )


def needs_query(action: Action) -> bool:
    return (
        action.kind in ("processes", "create", "mkdir", "copy", "move")
        or action.kind in ("find", "list")
        and bool(action.min_size_bytes or action.modified_after or action.file_type != "any")
    )


def describe_action(action: Action, cwd: Path, powershell: bool = False) -> str:
    if action.kind in ("delete", "read"):
        return (
            ("Permanently delete" if action.kind == "delete" else "Read file")
            + "\nPath: "
            + action.path
            + ("\nIncludes all its contents." if action.recursive else "")
        )
    if action.kind in ("create", "mkdir", "copy", "move"):
        names = {
            "create": "Create UTF-8 file (without overwriting)",
            "mkdir": "Create folder",
            "copy": "Copy file (without overwriting)",
            "move": "Move file (without overwriting)",
        }
        content = "".join(
            char if ord(char) >= 32 or char in "\n\t" else f"\\x{ord(char):02x}"
            for char in action.content
        )
        return (
            names[action.kind]
            + "\nPath: "
            + action.path
            + ("\nDestination: " + action.destination if action.destination else "")
            + ("\nContent:\n" + content if action.kind == "create" else "")
        )
    return (PowerShellAdapter() if powershell else CmdAdapter()).render(action, cwd)


def cmd_quote(value: str, batch: bool = True) -> str:
    if any(c in value for c in '\r\n\x00"'):
        raise ValueError("CMD does not allow quotes or control characters in this argument")
    # Batch files parse percent once; delayed expansion is disabled by the executor.
    return '"' + (value.replace("%", "%%") if batch else value) + '"'


def ps_quote(value: str) -> str:
    if "\x00" in value:
        raise ValueError("Invalid NUL")
    return "'" + value.replace("'", "''") + "'"


class CmdAdapter(ShellAdapter):
    def __init__(self, policy_token: str = "") -> None:
        self.policy_token = policy_token

    def render(self, action: Action, cwd: Path) -> str:
        if needs_query(action):
            return query_command(action, policy_token=self.policy_token)
        path = str((cwd / action.path).resolve()) if action.path else str(cwd)
        quoted = cmd_quote(path)
        if action.kind == "cd":
            return "cd /d " + quoted
        if action.kind == "clear":
            return "cls"
        if action.kind in ("list", "find"):
            if any(c in action.pattern for c in '\\/:"%!?&|<>^()'):
                raise ValueError("Invalid pattern")
            return (
                "dir "
                + ("/s /b " if action.recursive or action.kind == "find" else "")
                + cmd_quote(str(Path(path) / action.pattern))
            )
        if action.kind == "read":
            return "type " + quoted
        if action.kind == "delete":
            return ("rmdir /s /q " if action.recursive else "del /q ") + quoted
        if action.kind == "env":
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", action.name):
                raise ValueError("Invalid variable")
            return "set " + cmd_quote(action.name + "=" + action.value)
        return action.command


class PowerShellAdapter(ShellAdapter):
    def __init__(self, policy_token: str = "") -> None:
        self.policy_token = policy_token

    def render(self, action: Action, cwd: Path) -> str:
        if needs_query(action):
            return query_command(action, powershell=True, policy_token=self.policy_token)
        path = str((cwd / action.path).resolve()) if action.path else str(cwd)
        quoted = ps_quote(path)
        if action.kind == "cd":
            return "Set-Location -LiteralPath " + quoted + " -ErrorAction Stop"
        if action.kind == "clear":
            return "Clear-Host"
        if action.kind in ("list", "find"):
            return (
                "Get-ChildItem -LiteralPath "
                + quoted
                + " -Filter "
                + ps_quote(action.pattern)
                + (" -Recurse" if action.recursive or action.kind == "find" else "")
                + " -ErrorAction Stop"
            )
        if action.kind == "read":
            return "Get-Content -LiteralPath " + quoted + " -Encoding UTF8 -ErrorAction Stop"
        if action.kind == "delete":
            return (
                "Remove-Item -LiteralPath "
                + quoted
                + (" -Recurse" if action.recursive else "")
                + " -ErrorAction Stop"
            )
        if action.kind == "env":
            return (
                "[Environment]::SetEnvironmentVariable("
                + ps_quote(action.name)
                + ", "
                + ps_quote(action.value)
                + ", 'Process')"
            )
        return action.command
