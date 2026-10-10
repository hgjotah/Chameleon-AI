import base64
import ctypes
import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from chameleon import __version__
from chameleon.core.config import asset_dir, load_config, save_config
from chameleon.platform.windows.shells import ps_quote
from chameleon.platform.windows.system import (
    FOLDERS,
    hidden_run,
    known_folder,
    launch,
    shell_executable,
)

START = b"# >>> Chameleon AI >>>"
END = b"# <<< Chameleon AI <<<"


def path_add(existing: str, entry: str) -> str:
    if entry.rstrip("\\").casefold() in [p.rstrip("\\").casefold() for p in existing.split(";")]:
        return existing
    return existing.rstrip(";") + (";" if existing else "") + entry


def path_remove(existing: str, entry: str) -> str:
    return ";".join(
        p for p in existing.split(";") if p.rstrip("\\").casefold() != entry.rstrip("\\").casefold()
    )


def user_path() -> str:
    if os.name != "nt":
        return ""
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ) as key:
        try:
            return str(winreg.QueryValueEx(key, "Path")[0])
        except FileNotFoundError:
            return ""


def set_user_path(value: str) -> None:
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, value)
    # Announce Environment to Explorer; bounded send avoids an unresponsive window hang.
    result = ctypes.c_size_t()
    send = ctypes.windll.user32.SendMessageTimeoutW
    send.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    send.restype = ctypes.c_size_t
    environment = ctypes.c_wchar_p("Environment")
    send(0xFFFF, 0x1A, 0, ctypes.cast(environment, ctypes.c_void_p), 2, 3000, ctypes.byref(result))


def profile_paths() -> list[tuple[str, Path]]:
    profiles = []
    for shell in ("powershell", "pwsh"):
        try:
            result = hidden_run(
                [
                    shell_executable(shell),
                    "-NoProfile",
                    "-Command",
                    "[Console]::OutputEncoding=[Text.Encoding]::UTF8; $PROFILE.CurrentUserAllHosts",
                ],
                timeout=15,
                encoding="utf-8",
            )
            if result.returncode == 0 and result.stdout.strip():
                profiles.append((shell, Path(result.stdout.strip().lstrip("\ufeff"))))
        except OSError:
            continue
    return profiles


def profile_block(module: Path) -> bytes:
    encoded = base64.b64encode(str(module).encode("utf-8")).decode("ascii")
    loader = (
        "Import-Module ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
        + encoded
        + "')))\r\n"
    )
    return START + b"\r\n" + loader.encode("ascii") + END


def edit_profile(path: Path, module: Path, remove: bool = False) -> None:
    original = path.read_bytes() if path.exists() else b""
    content = render_profile(original, module, remove)
    if content == original:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if original:
        path.with_name(path.name + f".chameleon-backup-{time.time_ns()}").write_bytes(original)
    if remove and content in (b"", b"\xef\xbb\xbf"):
        path.unlink(missing_ok=True)
    else:
        path.write_bytes(content)


def render_profile(original: bytes, module: Path, remove: bool = False) -> bytes:
    # Work on original encoding; preserve every byte outside our exact block.
    utf16 = original.startswith((b"\xff\xfe", b"\xfe\xff"))
    encoding = (
        "utf-16-le" if original.startswith(b"\xff\xfe") else "utf-16-be" if utf16 else "utf-8"
    )
    begin = START.decode().encode(encoding)
    end = END.decode().encode(encoding)
    if (begin in original) != (end in original):
        raise ValueError(
            "Bloque de perfil incompleto. Repara manualmente los delimitadores de Chameleon."
        )
    content = original
    start = content.find(begin)
    if start >= 0:
        finish = content.find(end, start) + len(end)
        newline = "\r\n".encode(encoding)
        # The preceding newline belongs to our block only when it was appended by us.
        if start >= len(newline) and content[start - len(newline) : start] == newline:
            start -= len(newline)
        if content[finish : finish + len(newline)] == newline:
            finish += len(newline)
        content = content[:start] + content[finish:]
    if not remove:
        block = profile_block(module).decode("utf-8").encode(encoding)
        content += "\r\n".encode(encoding) + block + "\r\n".encode(encoding)
        # UTF8 BOM for Windows PowerShell 5.1; do not alter existing encoding.
        if not original:
            content = b"\xef\xbb\xbf" + content
    return content


def secure_runtime(root: Path) -> None:
    directory = root / "runtime"
    directory.mkdir(parents=True, exist_ok=True)
    result = hidden_run(["whoami", "/user", "/fo", "csv", "/nh"], timeout=10)
    import re

    match = re.search(r"S-1-5-[\d-]+", result.stdout)
    if not match:
        raise OSError("No se pudo obtener el SID para proteger runtime")
    acl = hidden_run(
        [
            "icacls",
            str(directory),
            "/inheritance:r",
            "/grant:r",
            f"*{match.group()}:(OI)(CI)F",
            "*S-1-5-18:(OI)(CI)F",
        ],
        timeout=15,
    )
    if acl.returncode:
        raise OSError("No se pudo proteger el runtime privado")


def shortcuts(root: Path, desktop: bool = False) -> None:
    programs = (
        Path(os.environ["APPDATA"])
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Chameleon AI"
    )
    programs.mkdir(parents=True, exist_ok=True)
    items = [
        ("Chameleon Terminal", root / "core" / "ChameleonTerminal.exe", ""),
        ("Chameleon Settings", root / "core" / "ChameleonSetup.exe", "settings"),
        ("Uninstall Chameleon", root / "core" / "ChameleonSetup.exe", "uninstall"),
    ]
    for name, target, arguments in items:
        link = programs / (name + ".lnk")
        script = f"$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut({ps_quote(str(link))}); $s.TargetPath={ps_quote(str(target))}; $s.Arguments={ps_quote(arguments)}; $s.WorkingDirectory={ps_quote(str(target.parent))}; $s.IconLocation={ps_quote(str(root / 'resources' / 'chameleon.ico'))}; $s.Save()"
        result = hidden_run(
            [shell_executable("powershell"), "-NoProfile", "-Command", script], timeout=20
        )
        if result.returncode:
            raise OSError("No se pudo crear el acceso directo: " + name)
        if desktop and name == "Chameleon Terminal":
            shutil.copy2(link, known_folder(FOLDERS["Desktop"]) / link.name)


def registration(root: Path, remove: bool = False) -> None:
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ChameleonAI"
    if remove:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            return
    else:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            values = {
                "DisplayName": "Chameleon AI",
                "DisplayVersion": __version__,
                "Publisher": "Chameleon AI",
                "InstallLocation": str(root),
                "UninstallString": '"' + str(root / "core" / "ChameleonSetup.exe") + '" uninstall',
                "DisplayIcon": str(root / "resources" / "chameleon.ico"),
            }
            for name, value in values.items():
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def install(
    root: Path,
    payload: Path,
    profiles: list[Path] | None = None,
    integrate: bool = True,
    desktop: bool = False,
    progress: Callable[[str], None] | None = None,
) -> None:
    if not (payload / "ChameleonCore.exe").is_file():
        raise OSError("Payload incompleto. Ejecuta scripts/build.ps1 primero.")
    if root.is_symlink() or (root.exists() and root.is_junction()):
        raise OSError("No se instala sobre enlaces o junctions")
    profile_list = profiles if profiles is not None else [p for _, p in profile_paths()]
    for profile in profile_list:
        # Validate all existing blocks before changing binaries or any integration.
        render_profile(
            profile.read_bytes() if profile.exists() else b"", root / "bin" / "Chameleon.psm1"
        )
    runtime = root / "runtime"
    if runtime.is_symlink() or (runtime.exists() and runtime.is_junction()):
        raise OSError("Runtime no puede ser un enlace o junction")
    if integrate:
        import psutil

        for process in psutil.process_iter(["pid", "exe"]):
            executable = process.info.get("exe")
            if (
                executable
                and process.pid != os.getpid()
                and Path(executable).is_relative_to(root / "core")
            ):
                raise OSError("Cierra Chameleon Terminal y Settings antes de Repair/Update.")
    root.mkdir(parents=True, exist_ok=True)
    previous = read_manifest(root)
    profile_list = list(dict.fromkeys(profile_list + [Path(p) for p in previous.get("profiles", [])]))
    for profile in profile_list:
        render_profile(profile.read_bytes() if profile.exists() else b"", root / "bin" / "Chameleon.psm1")
    required_bytes = sum(p.stat().st_size for p in payload.rglob("*") if p.is_file()) + 16 * 1024 * 1024
    if shutil.disk_usage(root).free < required_bytes:
        raise OSError(f"No hay espacio suficiente para instalar el runtime. Libera al menos {required_bytes // 1048576} MB y vuelve a intentarlo.")
    # Snapshot small integration files. Keep the old runtime until everything commits.
    affected = [root / "bin" / "chameleon.cmd", root / "bin" / "Chameleon.psm1",
                root / "resources" / "chameleon.ico", root / "install.json",
                root / "config" / "config.toml", *profile_list]
    if integrate:
        programs = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Chameleon AI"
        affected.extend(programs / (name + ".lnk") for name in ("Chameleon Terminal", "Chameleon Settings", "Uninstall Chameleon"))
        if desktop:
            affected.append(known_folder(FOLDERS["Desktop"]) / "Chameleon Terminal.lnk")
    snapshots = {p: p.read_bytes() if p.exists() else None for p in affected}
    old_path = user_path() if integrate else ""
    registry_values = []
    if integrate:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ChameleonAI") as key:
                for index in range(winreg.QueryInfoKey(key)[1]):
                    registry_values.append(winreg.EnumValue(key, index))
        except FileNotFoundError:
            pass
    # Copy into staging and validate all files before replacing any installed executable.
    staging = root / "runtime" / "staging"
    if staging.exists():
        shutil.rmtree(staging)
    if progress:
        progress("Copiando y verificando el runtime incluido…")
    shutil.copytree(payload, staging)
    hashes = {}
    for p in staging.rglob("*"):
        if p.is_file():
            with p.open("rb") as stream:
                hashes[str(p.relative_to(staging))] = hashlib.file_digest(stream, "sha256").hexdigest()
    if progress:
        progress("Runtime verificado. Configurando shells y accesos directos…")
    core = root / "core"
    backup = root / "runtime" / ("backup-" + uuid.uuid4().hex)
    replaced = False
    try:
        if core.exists():
            # A running installed GUI holds DLLs open. Setup is relaunched from an external copy by the bootstrap.
            core.rename(backup)
        staging.rename(core)
        replaced = True
        for directory in ("bin", "resources", "runtime", "config", "logs"):
            (root / directory).mkdir(exist_ok=True)
        shutil.copy2(asset_dir() / "shell" / "chameleon.cmd", root / "bin" / "chameleon.cmd")
        shutil.copy2(asset_dir() / "shell" / "Chameleon.psm1", root / "bin" / "Chameleon.psm1")
        shutil.copy2(asset_dir() / "icons" / "chameleon.ico", root / "resources" / "chameleon.ico")
        for profile in profile_list:
            edit_profile(profile, root / "bin" / "Chameleon.psm1")
        if integrate:
            secure_runtime(root)
            set_user_path(path_add(user_path(), str(root / "bin")))
            shortcuts(root, desktop)
            registration(root)
        config, _ = load_config(root)
        save_config(config, root)
        previous.update(
            {
                "version": __version__,
                "profiles": [str(p) for p in profile_list],
                "hashes": hashes,
                "desktop_shortcut": desktop or previous.get("desktop_shortcut", False),
            }
        )
        write_manifest(root, previous)
    except Exception:
        if replaced and core.exists():
            shutil.rmtree(core)
        if backup.exists():
            backup.rename(core)
        for path, original in snapshots.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(original)
        if integrate:
            set_user_path(old_path)
            if registry_values:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ChameleonAI") as key:
                    for name, value, kind in registry_values:
                        winreg.SetValueEx(key, name, 0, kind, value)
            else:
                registration(root, remove=True)
        raise
    if backup.exists():
        try:
            shutil.rmtree(backup)
        except OSError:
            logging.getLogger("chameleon").warning("Installed successfully; previous runtime cleanup deferred")



def read_manifest(root: Path) -> dict[str, Any]:
    path = root / "install.json"
    if not path.exists():
        return {}
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            raise ValueError("Manifest must be an object")
        return result
    except (ValueError, UnicodeError) as exc:
        raise ValueError("install.json está dañado. Conserva una copia y recupera el manifiesto antes de reparar o desinstalar.") from exc


def write_manifest(root: Path, manifest: dict[str, Any]) -> None:
    temporary = root / ("install-" + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        temporary.replace(root / "install.json")
    finally:
        temporary.unlink(missing_ok=True)


def uninstall_integration(root: Path, integrate: bool = True) -> None:
    manifest = read_manifest(root)
    for name in manifest.get("profiles", []):
        edit_profile(Path(name), root / "bin" / "Chameleon.psm1", remove=True)
    if integrate:
        set_user_path(path_remove(user_path(), str(root / "bin")))
        registration(root, remove=True)
        programs = (
            Path(os.environ["APPDATA"])
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Chameleon AI"
        )
        if programs.exists():
            shutil.rmtree(programs)
        if manifest.get("desktop_shortcut"):
            (known_folder(FOLDERS["Desktop"]) / "Chameleon Terminal.lnk").unlink(missing_ok=True)


def remove_installation(root: Path, delayed: bool = False) -> None:
    resolved = root.resolve()
    if (
        root.is_symlink()
        or root.is_junction()
        or not (root / "install.json").exists()
        or resolved == Path(resolved.anchor)
    ):
        raise OSError("Destino de desinstalación no válido")
    if delayed:
        # Powershell performs all filesystem operations, with a verified fixed target.
        script = f"Start-Sleep -Seconds 3; for($i=0;$i -lt 20;$i++){{try{{Remove-Item -LiteralPath {ps_quote(str(resolved))} -Recurse -Force -ErrorAction Stop; break}}catch{{Start-Sleep -Seconds 1}}}}"
        launch(
            [shell_executable("powershell"), "-NoProfile", "-Command", script],
            creationflags=0x08000000,
        )
    else:
        shutil.rmtree(resolved)
