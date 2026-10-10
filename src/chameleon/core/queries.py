import fnmatch
from collections.abc import Iterator
from pathlib import Path

import psutil

from chameleon.core.schemas import Action


def file_query(action: Action, cwd: Path) -> Iterator[Path]:
    root = (cwd / action.path).resolve() if action.path else cwd
    if not root.is_dir():
        raise ValueError("El directorio de búsqueda no existe")
    # Walk without following directory symlinks/junctions; protects from loops.
    if action.recursive or action.kind == "find":

        def entries() -> Iterator[Path]:
            for directory, names, files in root.walk(follow_symlinks=False):
                names[:] = [name for name in names if not (directory / name).is_junction()]
                for name in names + files:
                    yield directory / name

        candidates = entries()
    else:
        candidates = root.iterdir()
    cutoff = action.modified_after.timestamp() if action.modified_after else 0
    for path in candidates:
        if not fnmatch.fnmatch(path.name.casefold(), action.pattern.casefold()):
            continue
        try:
            if action.file_type == "file" and not path.is_file():
                continue
            if action.file_type == "directory" and not path.is_dir():
                continue
            stat = path.stat()
            if stat.st_size < action.min_size_bytes or stat.st_mtime < cutoff:
                continue
            yield path
        except (OSError, PermissionError):
            continue


def process_query(limit: int = 20) -> list[tuple[str, int, int]]:
    rows = []
    for process in psutil.process_iter(["name", "pid", "memory_info"]):
        try:
            memory = process.info["memory_info"]
            if memory:
                rows.append((str(process.info["name"]), int(process.info["pid"]), int(memory.rss)))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(rows, key=lambda row: row[2], reverse=True)[:limit]
