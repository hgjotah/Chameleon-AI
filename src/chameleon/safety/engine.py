import ntpath
import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from chameleon.core.config import SafetyConfig
from chameleon.core.schemas import Action, Plan
from chameleon.safety.permissions import denied


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

    def __init__(
        self,
        system_root: str = "C:\\Windows",
        strict: bool = False,
        policy: SafetyConfig | None = None,
    ) -> None:
        self.system_root = ntpath.normcase(ntpath.normpath(system_root))
        self.strict = strict
        self.policy = policy or SafetyConfig()

    def protected(self, value: str) -> bool:
        if self.policy.permissions()["system"]:
            return False
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
        reason = denied(action, self.policy)
        if reason:
            return Assessment(Risk.BLOCKED, reason)
        if self.policy.mode in ("full", "developer"):
            return Assessment(
                Risk.CONFIRM if self.policy.confirms() else Risk.SAFE,
                "Access " + self.policy.mode + " · Windows user permissions.",
            )
        if action.kind in ("create", "mkdir", "copy", "move"):
            from chameleon.core.files import validate_target

            target = (cwd / (action.destination or action.path)).resolve()
            try:
                validate_target(target)
            except ValueError as exc:
                return Assessment(Risk.BLOCKED, str(exc))
            if self.protected(str(target)) or action.kind == "move" and self.protected(action.path):
                return Assessment(
                    Risk.BLOCKED,
                    "Choose a user folder; protected system directories will not be changed.",
                )
            if target.exists():
                return Assessment(
                    Risk.BLOCKED, f"Ya existe {target}. Nothing was overwritten; choose another name."
                )
            if action.kind != "mkdir" and not target.parent.is_dir():
                return Assessment(
                    Risk.BLOCKED,
                    f"The destination folder does not exist: {target.parent}. Create that folder first.",
                )
            if action.kind in ("copy", "move") and not (cwd / action.path).is_file():
                return Assessment(Risk.BLOCKED, "The source file does not exist.")
            return Assessment(
                Risk.CONFIRM,
                "A folder will be created."
                if action.kind == "mkdir"
                else "Files will be changed. Review the destination and content.",
            )
        if action.kind == "delete":
            resolved = str((cwd / action.path).resolve())
            if self.protected(resolved) or self.protected(action.path):
                return Assessment(
                    Risk.BLOCKED, "Deleting the root or system directories is not allowed."
                )
            return Assessment(Risk.CONFIRM, "Files will be permanently deleted.")
        if action.kind == "env":
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", action.name):
                return Assessment(Risk.BLOCKED, "Invalid variable name.")
            if action.name.casefold() in {
                "comspec",
                "systemroot",
                "windir",
                "pathext",
                "path",
                "prompt",
            }:
                return Assessment(Risk.CONFIRM, "This will change an important variable in the current session.")
            return Assessment(Risk.CONFIRM, "This will change the current session environment.")
        if action.kind != "command":
            if action.kind in ("cd", "read", "delete") and not (cwd / action.path).exists():
                return Assessment(Risk.BLOCKED, "The path does not exist; destinations are never invented.")
            if action.kind in ("cd", "list", "find") and not (cwd / action.path).is_dir():
                return Assessment(Risk.BLOCKED, "The path must be an existing folder.")
            if action.kind == "read" and not (cwd / action.path).is_file():
                return Assessment(
                    Risk.BLOCKED, "Select an existing file to read its contents."
                )
            return Assessment(
                Risk.CONFIRM if self.strict else Risk.SAFE, "Query or navigation operation."
            )
        return self.command(action.command, cwd)

    def command(self, command: str, cwd: Path | None = None) -> Assessment:
        reason = denied(Action(kind="command", command=command), self.policy)
        if reason:
            return Assessment(Risk.BLOCKED, reason)
        from chameleon.safety.permissions import session_change, session_read

        if session_change(command):
            return Assessment(
                Risk.CONFIRM if self.strict else Risk.SAFE,
                "This will only change the current session appearance.",
            )
        if session_read(command):
            return Assessment(
                Risk.CONFIRM if self.strict else Risk.SAFE,
                "Query a session property.",
            )
        if (
            self.policy.mode in ("full", "developer")
            or self.policy.mode == "custom"
            and self.policy.permissions()["scripts"]
        ):
            return Assessment(
                Risk.CONFIRM if self.policy.confirms() else Risk.SAFE,
                "Command allowed by your access profile.",
            )
        if self.policy.mode == "custom":
            if cwd is not None and re.search(
                r"\b(?:del|erase|rd|rmdir|rm|remove-item|move|copy|ren|set-content|out-file)\b",
                command,
                re.I,
            ):
                for argument in re.findall(r'"[^"]*"|\x27[^\x27]*\x27|\S+', command):
                    value = argument.strip('"\x27')
                    if value.startswith(("/", "-")):
                        continue
                    if self.protected(str((cwd / value).resolve())):
                        return Assessment(
                            Risk.BLOCKED, "System targets are disabled in this profile."
                        )
            return Assessment(
                Risk.CONFIRM if self.policy.confirms() else Risk.SAFE,
                "Custom permissions: review the command.",
            )
        from chameleon.safety.permissions import READ_COMMANDS

        pieces = re.split(r"&&|\|\||[&;|]", command)
        if (
            not re.search(r"[<>^%!`$(){}]", command)
            and pieces
            and all(piece.strip().split(" ", 1)[0].casefold() in READ_COMMANDS for piece in pieces)
        ):
            return Assessment(
                Risk.CONFIRM if self.strict else Risk.SAFE, "Read-only query."
            )
        lowered = command.casefold()
        first_match = re.match(r'\s*["\x27]?([^\s"\x27]+)', lowered)
        first = ntpath.basename(first_match.group(1)).removesuffix(".exe") if first_match else ""
        if first_match and re.search(r"[\\/:]", first_match.group(1)):
            return Assessment(
                Risk.BLOCKED, "AI cannot run programs from an arbitrary path."
            )
        # Reject opaque execution, nested shells, interpolation that hides destructive targets,
        # and storage tools. These cannot be independently reasoned about from source strings.
        opaque = r"\b(?:format|diskpart|clear-disk|initialize-disk|remove-partition|format-volume|invoke-expression|iex|invoke-command|start-process|cmd|powershell|pwsh|python\d*|node|wscript|cscript|mshta|rundll32|regsvr32|certutil|bitsadmin|curl|wget)\b"
        if re.search(opaque, lowered) or re.search(r"-(?:enc|encodedcommand)\b", lowered):
            return Assessment(
                Risk.BLOCKED,
                "AI cannot run opaque code, nested shells, downloads or disk destruction tools.",
            )
        destructive = re.search(r"\b(?:del|erase|rd|rmdir|remove-item|rm|deltree)\b", lowered)
        if destructive:
            if re.search(
                r"[%!$*?]|\b(?:windows|system32|syswow64)\b|[a-z]:[\\/](?:[\s\x27\"]|$)", lowered
            ):
                return Assessment(Risk.BLOCKED, "Bulk, dynamic or protected destructive target.")
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
                            "The relative target resolves to a protected system directory.",
                        )
            return Assessment(Risk.CONFIRM, "The command may delete files.")
        if re.search(
            r"\b(?:move|ren|rename|reg\s+delete|remove-itemproperty)\b", lowered
        ) and re.search(
            r"\b(?:windows|system32|hklm|hkey_local_machine)\b|[a-z]:[\\/](?:[\s\x27\"]|$)", lowered
        ):
            return Assessment(
                Risk.BLOCKED, "Bulk changes to a protected system target."
            )
        # Metacharacters, expansions, redirection and compound syntax never enter SAFE.
        if re.search(r"[&|<>^%!`;\n\r$()]", command):
            return Assessment(
                Risk.CONFIRM, "Compound syntax: review the entire command before running it."
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
            return Assessment(Risk.CONFIRM if self.strict else Risk.SAFE, "Query or navigation.")
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
                "Executable not supported for AI-generated actions. Type it directly if you want to run it.",
            )
        return Assessment(
            Risk.CONFIRM, "This command changes the system or files. Review its effects.", admin
        )

    def assess(self, plan: Plan, cwd: Path) -> Assessment:
        if self.policy.mode in ("full", "developer"):
            return Assessment(
                Risk.CONFIRM if plan.actions and self.policy.confirms() else Risk.SAFE,
                "Perfil " + self.policy.mode + " · Windows user permissions.",
            )
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
                        "Plans with multiple actions must use structured cd navigation.",
                    )
                )
            else:
                decisions.append(self.action(action, current))
            if action.kind == "cd":
                current = (current / action.path).resolve()
        if not decisions:
            return Assessment(Risk.SAFE, "No execution.")
        worst = max(decisions, key=lambda d: d.level)
        return Assessment(
            Risk.SAFE
            if worst.level == Risk.CONFIRM and not self.policy.confirms()
            else worst.level,
            worst.reason,
            any(d.requires_admin for d in decisions),
        )
