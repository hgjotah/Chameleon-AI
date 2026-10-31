"""Bounded read-only tools used to ground model answers in observed facts."""

import os
import time
from pathlib import Path

from chameleon.core.context import Context
from chameleon.core.intents import resolve_path, resolve_reference
from chameleon.core.privacy import redact
from chameleon.core.queries import process_query
from chameleon.core.schemas import Action


def inspect_action(action: Action, context: Context) -> dict:
    target = resolve_path(action.path, context) if action.path else Path(context.cwd).resolve()
    if action.kind not in ("list", "find", "read", "processes"):
        raise ValueError("La inspección no admite modificaciones ni comandos.")
    result: dict = {"kind": action.kind, "path": str(target), "observed_at": time.time()}
    try:
        if action.kind == "read":
            target, matches = resolve_reference(action.path, context)
            if matches:
                raise ValueError("Nombre ambiguo; indica la extensión exacta: " + ", ".join(p.name for p in matches[:20]))
            result["path"] = str(target)
        allowed = [
            Path(context.cwd).resolve(),
            *(Path(p).resolve() for p in context.known_directories.values()),
        ]
        if action.kind != "processes" and not context.permissions.get('system') and not any(
            target == p or target.is_relative_to(p) for p in allowed
        ):
            raise ValueError(
                "La inspección está limitada a la carpeta actual y tus carpetas conocidas. Indica la ubicación y navega a ella primero."
            )
        if action.kind == "processes":
            result["processes"] = [
                {"name": n, "pid": p, "rss_bytes": m}
                for n, p, m in process_query(min(action.limit, 30))
            ]
        elif action.kind == "read":
            # Avoid pipes/devices and bound memory even if a file grows while read.
            if not target.is_file():
                raise ValueError("No es un archivo normal existente.")
            with target.open("rb") as stream:
                content = stream.read(12001)
            encoding = "utf-16" if content.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
            if encoding != "utf-16" and b"\0" in content:
                raise ValueError("Archivo binario; no se interpreta como texto.")
            result["content"] = redact(content[:12000].decode(encoding, errors="replace"))
            result["encoding"] = encoding
            result["truncated"] = len(content) > 12000
            result["size_bytes"] = target.stat().st_size
        else:
            if not target.is_dir():
                raise ValueError("La carpeta consultada no existe.")
            import fnmatch

            rows = []
            scanned = 0
            deadline = time.monotonic() + 3
            complete = True
            errors = []

            def error(exc: OSError) -> None:
                errors.append(type(exc).__name__)

            candidates = (
                os.walk(target, onerror=error, followlinks=False)
                if action.kind == "find" or action.recursive
                else [(str(target), [], os.listdir(target))]
            )
            for directory, directories, names in candidates:
                directories[:] = [
                    n
                    for n in directories
                    if not (Path(directory) / n).is_junction()
                    and not (Path(directory) / n).is_symlink()
                ]
                for name in directories + names:
                    scanned += 1
                    if scanned > 5000 or time.monotonic() > deadline:
                        complete = False
                        break
                    path = Path(directory) / name
                    if not fnmatch.fnmatch(name.casefold(), action.pattern.casefold()):
                        continue
                    try:
                        stat = path.stat()
                        kind = "directory" if path.is_dir() else "file"
                        if (
                            action.file_type not in ("any", kind)
                            or stat.st_size < action.min_size_bytes
                            or action.modified_after
                            and stat.st_mtime < action.modified_after.timestamp()
                        ):
                            continue
                        rows.append(
                            {
                                "path": str(path),
                                "type": kind,
                                "size_bytes": stat.st_size,
                                "modified_timestamp": stat.st_mtime,
                            }
                        )
                        if len(rows) >= 40:
                            complete = False
                            break
                    except OSError as exc:
                        error(exc)
                if not complete:
                    break
            result.update(
                entries=rows,
                complete=complete and not errors,
                matched_count=len(rows),
                scanned=scanned,
                errors=errors[:5],
            )
        result["ok"] = True
    except (OSError, ValueError) as exc:
        result.update(ok=False, error=str(exc))
    return result
