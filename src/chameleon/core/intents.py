import re
import shutil
import unicodedata
from pathlib import Path

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
    value = value.strip().strip('"').strip("'")
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
    key = aliases.get(normalize(value), value)
    match = next(
        (v for k, v in ctx.known_directories.items() if k.casefold() == key.casefold()), None
    )
    path = Path(match or value).expanduser()
    return (Path(ctx.cwd) / path).resolve() if not path.is_absolute() else path.resolve()


def local_plan(request: str, ctx: Context) -> Plan | None:
    text = normalize(request)

    def execute(action: Action, summary: str) -> Plan:
        return Plan(intent="execute", shell=ctx.shell, actions=[action], summary=summary)

    if text in ("limpiar", "limpia", "clear", "limpia la pantalla", "clear screen"):
        return execute(Action(kind="clear"), "Limpiar pantalla")
    if text in ("atras", "sube una carpeta", "up", "go back", "..", "back"):
        return execute(Action(kind="cd", path=str(Path(ctx.cwd).parent)), "Subir una carpeta")
    navigation = re.match(
        r"^(?:ve a|vete a|entra en|abre la carpeta|cambia a|go to|enter|open folder)\s+(.+)$",
        request,
        flags=re.I,
    )
    target = navigation.group(1) if navigation else request
    path = resolve_path(target, ctx)
    if path.is_dir():
        return execute(Action(kind="cd", path=str(path)), "Cambiar directorio")
    if navigation:
        return Plan(
            intent="clarify",
            shell=ctx.shell,
            summary=f"No se encontró la carpeta {target}. Indica una ruta existente.",
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
    deletion = re.match(
        r"^(?:elimina|borra|delete|remove)\s+(?:el archivo |the file )?(.+)$", request, re.I
    )
    if deletion:
        value = deletion.group(1).strip().strip('"').strip("'")
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
        target_path = resolve_path(value, ctx)
        if target_path.exists():
            return execute(
                Action(kind="delete", path=str(target_path), recursive=target_path.is_dir()),
                f"Eliminar {target_path}",
            )
        return Plan(
            intent="clarify",
            shell=ctx.shell,
            summary=f"El archivo {value} no existe. Indica una ruta existente.",
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
    builtins = CMD_BUILTINS if ctx.shell == "cmd" else PS_BUILTINS
    if first.casefold() in builtins | (aliases or set()):
        return True
    if shutil.which(first):
        return True
    path = Path(ctx.cwd) / first
    if path.is_file():
        return True
    return any(path.with_suffix(ext).is_file() for ext in (".exe", ".cmd", ".bat", ".ps1", ".com"))
