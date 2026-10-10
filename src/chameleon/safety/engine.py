import ntpath
import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from chameleon.core.schemas import Action, Plan


class Risk(IntEnum):
    SAFE = 0
    CONFIRM = 1
    BLOCKED = 2


@dataclass(frozen=True)
class Assessment:
    level: Risk
    reason: str
    requires_admin: bool = False


class RiskEngine:
    """Conservative independent policy. Model risk/confidence never grant permission."""

    def __init__(self, system_root: str = "C:\\Windows", strict: bool = False) -> None:
        self.system_root = ntpath.normcase(ntpath.normpath(system_root))
        self.strict = strict

    def protected(self, value: str) -> bool:
        path = ntpath.normcase(ntpath.normpath(value.strip('"\x27 ')))
        drive, tail = ntpath.splitdrive(path)
        if drive and tail in ("", "\\", "/"):
            return True
        root = self.system_root
        return (
            path == root
            or root.startswith(path.rstrip("\\") + "\\")
            or path.startswith(root + "\\")
        )

    def action(self, action: Action, cwd: Path) -> Assessment:
        if action.kind == "delete":
            resolved = str((cwd / action.path).resolve())
            if self.protected(resolved) or self.protected(action.path):
                return Assessment(
                    Risk.BLOCKED, "No se permite destruir la raíz ni directorios del sistema."
                )
            return Assessment(Risk.CONFIRM, "Los archivos se eliminarán de forma permanente.")
        if action.kind == "env":
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", action.name):
                return Assessment(Risk.BLOCKED, "Nombre de variable inválido.")
            if action.name.casefold() in {
                "comspec",
                "systemroot",
                "windir",
                "pathext",
                "path",
                "prompt",
            }:
                return Assessment(Risk.CONFIRM, "Cambiará una variable importante de esta sesión.")
            return Assessment(Risk.CONFIRM, "Cambiará el entorno de esta sesión.")
        if action.kind != "command":
            if action.kind in ("cd", "read", "delete") and not (cwd / action.path).exists():
                return Assessment(Risk.BLOCKED, "La ruta no existe; no se inventan destinos.")
            return Assessment(
                Risk.CONFIRM if self.strict else Risk.SAFE, "Operación de consulta o navegación."
            )
        return self.command(action.command, cwd)

    def command(self, command: str, cwd: Path | None = None) -> Assessment:
        lowered = command.casefold()
        first_match = re.match(r'\s*["\x27]?([^\s"\x27]+)', lowered)
        first = ntpath.basename(first_match.group(1)).removesuffix(".exe") if first_match else ""
        if first_match and re.search(r"[\\/:]", first_match.group(1)):
            return Assessment(
                Risk.BLOCKED, "La IA no puede ejecutar programas por una ruta arbitraria."
            )
        # Reject opaque execution, nested shells, interpolation that hides destructive targets,
        # and storage tools. These cannot be independently reasoned about from source strings.
        opaque = r"\b(?:format|diskpart|clear-disk|initialize-disk|remove-partition|format-volume|invoke-expression|iex|invoke-command|start-process|cmd|powershell|pwsh|python\d*|node|wscript|cscript|mshta|rundll32|regsvr32|certutil|bitsadmin|curl|wget)\b"
        if re.search(opaque, lowered) or re.search(r"-(?:enc|encodedcommand)\b", lowered):
            return Assessment(
                Risk.BLOCKED,
                "La IA no puede ejecutar código opaco, shells anidados, descargas ni herramientas de destrucción de discos.",
            )
        destructive = re.search(r"\b(?:del|erase|rd|rmdir|remove-item|rm|deltree)\b", lowered)
        if destructive:
            if re.search(
                r"[%!$*?]|\b(?:windows|system32|syswow64)\b|[a-z]:[\\/](?:[\s\x27\"]|$)", lowered
            ):
                return Assessment(Risk.BLOCKED, "Destino destructivo masivo, dinámico o protegido.")
            if cwd is not None:
                arguments = re.findall(
                    r'"[^"]*"|\x27[^\x27]*\x27|\S+', command[destructive.end() :]
                )
                for argument in arguments:
                    value = argument.strip('"\x27')
                    if value.startswith(("/", "-")) or value in ("&", "|", ";"):
                        continue
                    if self.protected(str((cwd / value).resolve())):
                        return Assessment(
                            Risk.BLOCKED,
                            "El destino relativo resuelve a un directorio protegido del sistema.",
                        )
            return Assessment(Risk.CONFIRM, "El comando puede eliminar archivos.")
        if re.search(
            r"\b(?:move|ren|rename|reg\s+delete|remove-itemproperty)\b", lowered
        ) and re.search(
            r"\b(?:windows|system32|hklm|hkey_local_machine)\b|[a-z]:[\\/](?:[\s\x27\"]|$)", lowered
        ):
            return Assessment(
                Risk.BLOCKED, "Modificación masiva de un destino protegido del sistema."
            )
        # Metacharacters, expansions, redirection and compound syntax never enter SAFE.
        if re.search(r"[&|<>^%!`;\n\r$()]", command):
            return Assessment(
                Risk.CONFIRM, "Sintaxis compuesta: revisa el comando completo antes de ejecutarlo."
            )
        safe = {
            "dir",
            "cd",
            "chdir",
            "cls",
            "type",
            "ipconfig",
            "ping",
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
        }
        if first in safe or (
            first == "git"
            and re.fullmatch(r"git\s+(?:status|diff|log|show)(?:\s+--?[\w=-]+)*", lowered)
            and not re.search(r"--(?:output|ext-diff|textconv|exec-path|paginate)|\s-c\b", lowered)
        ):
            return Assessment(Risk.CONFIRM if self.strict else Risk.SAFE, "Consulta o navegación.")
        admin = bool(
            re.search(
                r"\b(?:sc|reg|netsh|bcdedit|stop-service|set-service|set-executionpolicy|restart-computer|stop-computer|shutdown|takeown|icacls)\b",
                lowered,
            )
        )
        if first not in {
            "git",
            "taskkill",
            "stop-process",
            "sc",
            "reg",
            "netsh",
            "shutdown",
            "icacls",
            "takeown",
            "winget",
            "set-service",
            "stop-service",
            "restart-service",
            "restart-computer",
            "stop-computer",
            "set-executionpolicy",
            "copy",
            "move",
            "ren",
            "mkdir",
            "md",
            "new-item",
            "set-content",
            "add-content",
            "set-itemproperty",
            "remove-itemproperty",
            "set-acl",
        }:
            return Assessment(
                Risk.BLOCKED,
                "Ejecutable no admitido para acciones generadas por IA. Escríbelo directamente si deseas ejecutarlo.",
            )
        return Assessment(
            Risk.CONFIRM, "Este comando modifica el sistema o archivos. Revisa sus efectos.", admin
        )

    def assess(self, plan: Plan, cwd: Path) -> Assessment:
        decisions = []
        current = cwd
        for action in plan.actions:
            if (
                len(plan.actions) > 1
                and action.kind == "command"
                and re.match(r"\s*(?:cd|chdir)\b", action.command, re.I)
            ):
                decisions.append(
                    Assessment(
                        Risk.BLOCKED,
                        "Los planes con varias acciones deben usar navegación cd estructurada.",
                    )
                )
            else:
                decisions.append(self.action(action, current))
            if action.kind == "cd":
                current = (current / action.path).resolve()
        if not decisions:
            return Assessment(Risk.SAFE, "Sin ejecución.")
        worst = max(decisions, key=lambda d: d.level)
        return Assessment(
            worst.level,
            worst.reason,
            plan.requires_admin or any(d.requires_admin for d in decisions),
        )
