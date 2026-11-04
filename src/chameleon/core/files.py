"""Literal file operations shared by all shells; never interpolate user content."""

import os
import re
import shutil
from pathlib import Path

from chameleon.core.schemas import Action


def validate_target(path: Path) -> None:
    if os.name != "nt":
        return
    for part in path.parts[1:]:
        if (
            re.search(r'[<>:"|?*\x00-\x1f]', part)
            or part.endswith((" ", "."))
            or re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part, re.I)
        ):
            raise ValueError(f"Invalid Windows filename: {part}")


def apply_file_action(action: Action) -> str:
    source = Path(action.path).resolve()
    validate_target(source)
    if action.kind == "mkdir":
        source.mkdir(parents=True, exist_ok=False)
        return f"Folder created: {source}"
    target = Path(action.destination).resolve() if action.destination else source
    validate_target(target)
    if not target.parent.is_dir():
        raise FileNotFoundError(f"The destination folder does not exist: {target.parent}. Create the folder first or choose another path.")
    if action.kind == "create":
        with source.open("x", encoding="utf-8", newline="") as stream:
            stream.write(action.content)
        return f"File created: {source}"
    if action.kind not in ("copy", "move"):
        raise ValueError("Unsupported file operation")
    if not source.is_file():
        raise ValueError(f"The source must be an existing file: {source}")
    # Exclusive creation guarantees that a destination appearing after approval
    # cannot be overwritten. Delete only our own incomplete copy on failure.
    with target.open("xb") as output:
        try:
            with source.open("rb") as input_stream:
                shutil.copyfileobj(input_stream, output, 1024 * 1024)
        except BaseException:
            output.close()
            target.unlink(missing_ok=True)
            raise
    if action.kind == "move":
        source.unlink()
    return f"File {"moved" if action.kind == 'move' else "copied"}: {target}"
