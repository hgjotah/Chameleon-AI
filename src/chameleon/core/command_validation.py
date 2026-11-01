"""Ground simple file-operation proposals in their verified operands.

This validates a model's choice; it never substitutes a stored task/command answer.
Complex requests without a single verified operation are not inferred here.
"""

import re
from pathlib import Path

from chameleon.core.context import Context


def candidate_error(command: str, context: Context) -> str:
    task = context.requested_action
    kind = task.get("kind", "")
    if not kind:
        return ""
    first = command.split(maxsplit=1)[0].casefold()
    families = {
        "read": {"type", "cat", "gc", "get-content"},
        "delete": {"del", "erase", "rd", "rmdir", "rm", "remove-item"},
        "copy": {"copy", "cp", "copy-item", "xcopy"},
        "move": {"move", "mv", "move-item"},
        "cd": {"cd", "chdir", "sl", "set-location", "pushd", "push-location"},
        "mkdir": {"mkdir", "md", "ni", "new-item"},
        "create": {"echo", "type", "copy", "ni", "new-item", "set-content", "out-file"},
        "clear": {"cls", "clear", "clear-host"},
        "list": {"dir", "ls", "gci", "get-childitem"},
        "find": {"dir", "ls", "gci", "get-childitem"},
    }
    if kind in families and first not in families[kind]:
        return (
            "The proposed operation does not match the verified task: "
            + kind
            + ". Choose an appropriate direct native operation; do not replace it with another task or an interpreter."
        )
    if context.shell == "cmd" and kind in ("read", "delete", "mkdir", "copy", "move"):
        # A simple verified task has fixed arity. Quoted spaces remain ONE
        # operand; prose accidentally emitted between operands is not syntax.
        tokens = re.findall(r'"[^"]*"|[^\s]+', command)[1:]
        if not re.search(r"[&|<>]", command):
            operands = [token for token in tokens if not token.startswith("/")]
            expected = 2 if kind in ("copy", "move") else 1
            if len(operands) != expected:
                return f"The direct {kind} operation needs {expected} literal operand(s). Your command has {len(operands)}. Do not insert natural-language words as arguments; quote filenames containing spaces."
    # Literal filenames/operands are data, not model-invented names. This is a
    # necessary check, not a claim of complete shell semantic equivalence.
    visible = command.replace("''", "'").casefold()
    for role in ("path", "destination"):
        value = task.get(role)
        if not value:
            continue
        path = Path(value)
        variants = [str(path)]
        if path.is_relative_to(context.cwd):
            variants.append(str(path.relative_to(context.cwd)))
        if not any(v.casefold() in visible for v in variants):
            return (
                "The command lost the exact "
                + role
                + " operand: "
                + value
                + ". Preserve the verified source/destination and quote spaces."
            )
    if (
        kind == "create"
        and task.get("content")
        and task["content"] not in command.replace("''", "'")
    ):
        return (
            "The command lost or changed the requested literal file content. Preserve it exactly."
        )
    return ""
