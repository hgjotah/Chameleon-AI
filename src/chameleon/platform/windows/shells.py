import base64
import re
import sys
from pathlib import Path

from chameleon.core.schemas import Action
from chameleon.platform.base import ShellAdapter


def query_command(action: Action, powershell: bool = False) -> str:
    encoded = base64.b64encode(action.model_dump_json().encode("utf-8")).decode("ascii")
    quote = ps_quote if powershell else cmd_quote
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).with_name("ChameleonCore.exe")
        command = quote(str(executable))
    else:
        command = quote(sys.executable) + " -m chameleon"
    operation = "apply" if action.kind in ("create", "mkdir", "copy", "move") else "query"
    result = ("& " if powershell else "") + command + " " + operation + " --encoded " + encoded
    if not powershell and len(result) > 7900:
        raise ValueError("La acción supera la longitud máxima de CMD. Reduce el contenido o usa una sesión PowerShell.")
    return result + ("; if ($LASTEXITCODE -ne 0) { throw 'Chameleon: no se pudo completar la acción' }" if powershell else "")


def needs_query(action: Action) -> bool:
    return (
        action.kind in ("processes", "create", "mkdir", "copy", "move")
        or action.kind in ("find", "list")
        and bool(action.min_size_bytes or action.modified_after or action.file_type != "any")
    )


def describe_action(action: Action, cwd: Path, powershell: bool = False) -> str:
    if action.kind in ("delete", "read"):
        return ("Eliminar permanentemente" if action.kind == "delete" else "Leer archivo") + "\nRuta: " + action.path + ("\nIncluye su contenido completo." if action.recursive else "")
    if action.kind in ("create", "mkdir", "copy", "move"):
        names = {"create": "Crear archivo UTF-8 (sin sobrescribir)", "mkdir": "Crear carpeta", "copy": "Copiar archivo (sin sobrescribir)", "move": "Mover archivo (sin sobrescribir)"}
        content = "".join(char if ord(char) >= 32 or char in "\n\t" else f"\\x{ord(char):02x}" for char in action.content)
        return names[action.kind] + "\nRuta: " + action.path + ("\nDestino: " + action.destination if action.destination else "") + ("\nContenido:\n" + content if action.kind == "create" else "")
    return (PowerShellAdapter() if powershell else CmdAdapter()).render(action, cwd)


def cmd_quote(value: str, batch: bool = True) -> str:
    if any(c in value for c in '\r\n\x00"'):
        raise ValueError("CMD no admite comillas ni controles en este argumento")
    # Batch files parse percent once; delayed expansion is disabled by the executor.
    return '"' + (value.replace("%", "%%") if batch else value) + '"'


def ps_quote(value: str) -> str:
    if "\x00" in value:
        raise ValueError("Invalid NUL")
    return "'" + value.replace("'", "''") + "'"


class CmdAdapter(ShellAdapter):
    def render(self, action: Action, cwd: Path) -> str:
        if needs_query(action):
            return query_command(action)
        path = str((cwd / action.path).resolve()) if action.path else str(cwd)
        quoted = cmd_quote(path)
        if action.kind == "cd":
            return "cd /d " + quoted
        if action.kind == "clear":
            return "cls"
        if action.kind in ("list", "find"):
            if any(c in action.pattern for c in '\\/:"%!?&|<>^()'):
                raise ValueError("Patrón inválido")
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
                raise ValueError("Variable inválida")
            return "set " + cmd_quote(action.name + "=" + action.value)
        return action.command


class PowerShellAdapter(ShellAdapter):
    def render(self, action: Action, cwd: Path) -> str:
        if needs_query(action):
            return query_command(action, powershell=True)
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
            return "Remove-Item -LiteralPath " + quoted + (" -Recurse" if action.recursive else "") + " -ErrorAction Stop"
        if action.kind == "env":
            return (
                "[Environment]::SetEnvironmentVariable("
                + ps_quote(action.name)
                + ", "
                + ps_quote(action.value)
                + ", 'Process')"
            )
        return action.command
