"""Direct invocation of an explicitly named existing script; no code generation."""

import re
from pathlib import Path

from chameleon.core.context import Context
from chameleon.platform.windows.shells import cmd_quote, ps_quote


def existing_script(request: str, context: Context) -> tuple[Path, str] | None:
    match = re.fullmatch(
        r"""\s*(?:ejecuta|ejecutar|corre|run|execute)\s+(?:(?:el|the)\s+)?(?:script\s+)?("[^"]+\.(?:cmd|bat|ps1|py|js)"|'[^']+\.(?:cmd|bat|ps1|py|js)'|[^\s]+\.(?:cmd|bat|ps1|py|js))\s*""",
        request,
        re.I,
    )
    if not match:
        return None
    from chameleon.core.intents import resolve_path

    target = resolve_path(match[1], context)
    if not target.is_file():
        raise FileNotFoundError("El script indicado no existe: " + str(target))
    relative = target.is_relative_to(context.cwd)
    name = str(target.relative_to(context.cwd)) if relative else str(target)
    suffix = target.suffix.casefold()
    if context.shell == "cmd":
        interpreter = {
            ".cmd": "call",
            ".bat": "call",
            ".ps1": "powershell -NoProfile -File",
            ".py": "python",
            ".js": "node",
        }[suffix]
        command = interpreter + " " + cmd_quote(name, batch=False)
    else:
        if suffix in (".ps1", ".cmd", ".bat"):
            command = "& " + ps_quote((".\\" if relative else "") + name)
        else:
            command = ("python" if suffix == ".py" else "node") + " " + ps_quote(name)
    return target, command
