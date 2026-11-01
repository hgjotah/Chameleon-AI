import re
import shutil
import unicodedata
from pathlib import Path
from typing import Literal

from chameleon.core.context import Context
from chameleon.core.schemas import Action, Plan

CMD_BUILTINS = set(
    "assoc break call cd chdir cls color copy date del dir echo endlocal erase exit for ftype goto if md mkdir mklink move path pause popd prompt pushd rd rem ren rename rmdir set setlocal shift start time title type ver verify vol".split()
)
PS_BUILTINS = set(
    "cd cls dir ls cat echo pwd clear sl gci gc rm del cp mv ni gi gps ps kill where select sort ft fl foreach measure help man history get-help get-command get-alias set-location get-childitem get-content get-process write-output invoke-item import-module exit".split()
)


def normalize(text: str) -> str:
    return (
        "".join(
            c
            for c in unicodedata.normalize("NFD", text.casefold())
            if unicodedata.category(c) != "Mn"
        )
        .strip()
        .rstrip(".")
    )


def resolve_path(value: str, ctx: Context) -> Path:
    value = unquote(value)
    aliases = {
        "descargas": "Downloads",
        "documentos": "Documents",
        "escritorio": "Desktop",
        "imagenes": "Pictures",
        "musica": "Music",
        "videos": "Videos",
        "casa": "home",
        "inicio": "home",
        "~": "home",
    }
    first, separator, remainder = value.replace("\\", "/").partition("/")
    key = aliases.get(normalize(first), first)
    match = next(
        (v for k, v in ctx.known_directories.items() if k.casefold() == key.casefold()), None
    )
    path = (
        (Path(match) / remainder if separator else Path(match))
        if match
        else Path(value).expanduser()
    )
    return (Path(ctx.cwd) / path).resolve() if not path.is_absolute() else path.resolve()


def unquote(value: str) -> str:
    value = value.strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'" else value


def resolve_reference(value: str, ctx: Context) -> tuple[Path, list[Path]]:
    """Resolve named files in a folder without treating Spanish prose as a path."""
    literal = resolve_path(value, ctx)
    # Typed model paths are data: a directory/file containing "de" or "en"
    # must not be reinterpreted as a natural-language location clause.
    if Path(unquote(value)).is_absolute() or literal.exists():
        target = literal
    else:
        value = re.sub(
            r"^(?:(?:el|la|un|una|the|a)\s+)?(?:archivo|fichero|carpeta|directorio|file|folder)\s+",
            "",
            value.strip(),
            flags=re.I,
        )
        value = re.sub(r"^(?:llamado|llamada|named|called)\s+", "", value, flags=re.I)
        named = split_phrase(value, r"\s+(?:llamado|llamada|named|called)\s+")
        if named and re.match(r"^(?:en|in|dentro de)\s+", named[0], re.I):
            folder = re.sub(
                r"^(?:en|in|dentro de)\s+(?:(?:la|el|the)\s+)?(?:(?:carpeta|directorio|folder)\s+)?",
                "",
                named[0],
                flags=re.I,
            )
            target = resolve_path(folder, ctx) / unquote(named[1])
        else:
            location = split_phrase(
                value,
                r"\s+(?:en|in|dentro de|de|from)\s+(?:(?:la|el|the)\s+)?(?:(?:carpeta|directorio|folder)\s+)?",
            )
            target = (
                resolve_path(location[1], ctx) / unquote(location[0])
                if location
                else resolve_path(value, ctx)
            )
    target = target.resolve()
    if target.exists() or target.suffix or not target.parent.is_dir():
        return target, []
    # Windows Explorer commonly hides extensions. Only match the exact stem;
    # ambiguity must be resolved by the user before a destructive action.
    from itertools import islice

    matches = [
        p
        for p in islice(target.parent.iterdir(), 5000)
        if p.is_file() and p.stem.casefold() == target.name.casefold()
    ]
    return (matches[0], []) if len(matches) == 1 else (target, sorted(matches))


CREATE = re.compile(
    r"^(?:crea(?:me)?|créame|crear|haz(?:me)?|genera|create|make)\s+(?:(?:un|una|el|la|a|the)\s+)?"
    r"(?P<kind>archivo|fichero|documento|carpeta|directorio|file|folder|directory)\b"
    r"(?:\s+de texto)?(?:\s+(?:nuevo|nueva|new))?(?:\s+(?:llamado|llamada|con (?:el )?nombre|named|called))?\s*(?P<rest>.*)$",
    re.I | re.S,
)


def split_phrase(value: str, expression: str) -> tuple[str, str] | None:
    quoted = ""
    protected: set[int] = set()
    for index, char in enumerate(value):
        if quoted:
            protected.add(index)
            if char == quoted:
                quoted = ""
        elif char in "\"'" and (index == 0 or value[index - 1].isspace()):
            quoted = char
            protected.add(index)
    for match in re.finditer(expression, value, re.I):
        if not any(index in protected for index in range(match.start(), match.end())):
            return value[: match.start()].strip(), value[match.end() :].strip()
    return None


def refine_request(original: str, answer: str, plan: Plan) -> str:
    """Keep the requested operation when asking for a name or destination."""
    creation = CREATE.match(original)
    if creation and not creation.group("rest").strip():
        return original.rstrip() + " " + answer
    if creation and plan.summary.startswith("Indica el nombre"):
        return original[: creation.start("rest")] + answer + " " + creation.group("rest")
    if normalize(original).startswith(("elimina", "borra", "delete", "remove")):
        return "elimina " + answer
    if normalize(original).startswith(("ve a", "vete a", "entra en", "go to", "open folder")):
        return "ve a " + answer
    return original + "; aclaración: " + answer


def local_plan(request: str, ctx: Context) -> Plan | None:
    from chameleon.core.scripts import existing_script

    try:
        script = existing_script(request, ctx)
    except FileNotFoundError as exc:
        return Plan(intent="error", shell=ctx.shell, summary=str(exc))
    if script:
        return Plan(
            intent="execute",
            shell=ctx.shell,
            summary=script[1],
            actions=[Action(kind="command", command=script[1])],
        )
    request = re.sub(
        r"^(?:por favor[, ]+|quiero que |puedes |podr[ií]as )", "", request.strip(), flags=re.I
    )
    text = normalize(request)

    # A single-action grammar must never absorb an additional instruction as a
    # filename/content. Quoted conjunctions remain literal data.
    if split_phrase(
        request,
        r"\s+(?:y luego|y despues|y despu[eé]s|despu[eé]s|and then|then|y (?:borra|elimina|crea|mueve|copia|lista|ejecuta)|and (?:delete|remove|create|move|copy|list|run))\s+",
    ):
        return None

    def execute(action: Action, summary: str) -> Plan:
        return Plan(intent="execute", shell=ctx.shell, actions=[action], summary=summary)

    creation = CREATE.match(request)
    if creation:
        directory = normalize(creation.group("kind")) in (
            "carpeta",
            "directorio",
            "folder",
            "directory",
        )
        rest = creation.group("rest").strip()
        if not rest:
            return Plan(
                intent="clarify",
                shell=ctx.shell,
                summary="¿Qué nombre o ruta quieres para la carpeta?"
                if directory
                else "¿Qué nombre o ruta quieres para el archivo?",
            )
        if re.match(r"^(?:en|in|con (?:contenido|texto)|with (?:content|text))\b", rest, re.I):
            return Plan(
                intent="clarify",
                shell=ctx.shell,
                summary="Indica el nombre del archivo o carpeta que quieres crear.",
            )
        parts = split_phrase(
            rest,
            r"\s+(?:con (?:el )?(?:contenido|texto)|que (?:contenga|diga)|with (?:the )?(?:content|text))\s*:?\s*",
        )
        name, content = (parts[0], unquote(parts[1])) if parts else (rest, "")
        location = split_phrase(
            name,
            r"\s+(?:en|in|dentro de)\s+(?:(?:la|el|the)\s+)?(?:(?:carpeta|directorio|folder)\s+)?",
        )
        creation_target = (
            resolve_path(location[1], ctx) / unquote(location[0])
            if location
            else resolve_path(name, ctx)
        )
        return execute(
            Action(
                kind="mkdir" if directory else "create", path=str(creation_target), content=content
            ),
            f"Crear {'carpeta' if directory else 'archivo'}: {creation_target}"
            + (f"\nContenido:\n{content}" if content else ""),
        )
    reading = re.match(
        r"^(?:lee|leer|muestra el contenido de|read|show contents of)\s+(?:(?:el archivo|the file)\s+)?(.+)$",
        request,
        re.I,
    )
    if reading:
        target, matches = resolve_reference(reading.group(1), ctx)
        if matches:
            return Plan(
                intent="clarify",
                shell=ctx.shell,
                summary="El nombre corresponde a varios archivos. Selecciona la ruta exacta.",
                choices=[str(p) for p in matches[:20]],
            )
        return execute(Action(kind="read", path=str(target)), f"Leer {target}")
    transfer = re.match(
        r"^(copia|copiar|mueve|mover|copy|move)\s+(?:(?:el archivo|the file)\s+)?(.+?)\s+(?:a|al|to)\s+(.+)$",
        request,
        re.I,
    )
    if transfer:
        source, matches = resolve_reference(transfer.group(2), ctx)
        if matches:
            return Plan(
                intent="clarify",
                shell=ctx.shell,
                summary="Hay varios archivos de origen. Selecciona la ruta exacta.",
                choices=[str(p) for p in matches[:20]],
            )
        target = resolve_path(transfer.group(3), ctx)
        if target.is_dir():
            target /= source.name
        kind: Literal["copy", "move"] = (
            "copy" if normalize(transfer.group(1)).startswith("cop") else "move"
        )
        return execute(
            Action(kind=kind, path=str(source), destination=str(target)),
            f"{'Copiar' if kind == 'copy' else 'Mover'} {source} → {target}",
        )
    if text in ("limpiar", "limpia", "clear", "limpia la pantalla", "clear screen"):
        return execute(Action(kind="clear"), "Limpiar pantalla")
    if text in ("atras", "sube una carpeta", "up", "go back", "..", "back"):
        return execute(Action(kind="cd", path=str(Path(ctx.cwd).parent)), "Subir una carpeta")
    navigation = re.match(
        r"^(?:ve a|vete a|entra en|abre la carpeta|cambia a|go to|enter|open folder)\s+(.+)$",
        request,
        flags=re.I,
    )
    navigation_target = navigation.group(1) if navigation else request
    path = resolve_path(navigation_target, ctx)
    if path.is_dir():
        return execute(Action(kind="cd", path=str(path)), "Cambiar directorio")
    if navigation:
        return Plan(
            intent="clarify",
            shell=ctx.shell,
            summary=f"No se encontró la carpeta {navigation_target}. Indica una ruta existente.",
        )
    if text in (
        "muestrame los archivos",
        "muestra los archivos",
        "lista los archivos",
        "list files",
        "show files",
    ):
        return execute(Action(kind="list", path=ctx.cwd), "Listar archivos")
    if text in (
        "muestra los procesos",
        "lista procesos",
        "show processes",
        "list processes",
        "dime que proceso esta usando mas ram",
    ):
        return execute(Action(kind="processes", limit=20), "Procesos ordenados por memoria RAM")
    if re.fullmatch(
        r"(?:muestra|muestrame|lista|show|list) (?:los |the )?(?:procesos|processes)(?: (?:que usan mas (?:memoria|ram)|using (?:the )?most (?:memory|ram)|por (?:memoria|ram)))?",
        text,
    ):
        return execute(Action(kind="processes", limit=20), "Procesos ordenados por memoria RAM")
    if re.fullmatch(
        r"(?:lista|muestra|muestrame|encuentra|busca|find|list|show)(?:me)?(?: todos)?(?: los)?(?: archivos)?(?: de)? (?:pdf|pdfs)",
        text,
    ):
        return execute(
            Action(
                kind="find" if text.startswith(("encuentra", "busca", "find")) else "list",
                path=ctx.cwd,
                pattern="*.pdf",
                recursive=text.startswith(("encuentra", "busca", "find")),
            ),
            "Listar PDF",
        )
    deletion = re.match(r"^(?:elimina|eliminar|borra|borrar|delete|remove)\s+(.+)$", request, re.I)
    if deletion:
        value = re.sub(
            r"^(?:(?:el|la|un|una|the|a)\s+)?(?:archivo|fichero|file)\s+",
            "",
            deletion.group(1).strip(),
            flags=re.I,
        )
        if normalize(value) in ("viejo", "old", "archivo viejo", "old file"):
            candidates = [
                entry.rstrip("/")
                for entry in ctx.entries
                if any(word in normalize(entry) for word in ("old", "viejo", "backup"))
            ]
            return Plan(
                intent="clarify",
                shell=ctx.shell,
                summary="Indica el archivo exacto que quieres eliminar.",
                choices=candidates[:20],
            )
        target_path, matches = resolve_reference(value, ctx)
        if (
            not target_path.exists()
            and not matches
            and (
                re.search(r"[*?]", value)
                or re.match(
                    r"^(?:todos?|todas?|all|every|each|los archivos|las carpetas)\b",
                    normalize(value),
                )
                or re.search(
                    r"\b(?:excepto|anteriores|posteriores|modificados|older|newer|except|modified)\b",
                    normalize(value),
                )
            )
        ):
            # A glob/filter is a task for the model, not a nonexistent literal
            # filename that the single-file grammar can authoritatively reject.
            return None
        if matches:
            return Plan(
                intent="clarify",
                shell=ctx.shell,
                summary="Hay varios archivos con ese nombre. Elige la ruta exacta que quieres eliminar.",
                choices=[str(p) for p in matches[:20]],
            )
        if target_path.exists():
            return execute(
                Action(kind="delete", path=str(target_path), recursive=target_path.is_dir()),
                f"Eliminar {target_path}",
            )
        return Plan(
            intent="clarify",
            shell=ctx.shell,
            summary=f"No se encontró el destino comprobado: {target_path}. Indica una ruta existente.",
        )
    return None


def is_real_command(text: str, ctx: Context, aliases: set[str] | None = None) -> bool:
    """The renderer leaves shell editing to the real shell; only completed lines are classified."""
    stripped = text.lstrip()
    if not stripped or stripped.startswith(("#", "$", "&", ". ", "(", "{", "@")):
        return True
    match = re.match(r'^(?:"([^"]+)"|\x27([^\x27]+)\x27|(\S+))', stripped)
    if not match:
        return True
    first = next(part for part in match.groups() if part is not None)
    if ctx.shell != "cmd" and re.fullmatch(r"[A-Za-z]+-[A-Za-z][A-Za-z0-9]*", first):
        # User-typed cmdlets (including not-yet-imported modules) stay native.
        # Generated commands have a separate AST/existence validation path.
        return True
    builtins = CMD_BUILTINS if ctx.shell == "cmd" else PS_BUILTINS
    if first.casefold() in builtins | (aliases or set()):
        return True
    if shutil.which(first):
        return True
    path = Path(ctx.cwd) / first
    if path.is_file():
        return True
    return any(path.with_suffix(ext).is_file() for ext in (".exe", ".cmd", ".bat", ".ps1", ".com"))
