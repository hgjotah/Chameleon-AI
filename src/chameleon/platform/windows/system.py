import ctypes
import os
import shutil
import subprocess
import sys
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from chameleon.platform.base import PlatformAdapter

_spawn_lock = threading.RLock()


def child_environment(environment: dict[str, str] | None = None, executable: str = "") -> dict[str, str]:
    result = dict(os.environ if environment is None else environment)
    if Path(executable).name.casefold() in ("powershell.exe", "pwsh.exe"):
        # Python intermediaries preserve PowerShell 7's module path. Windows
        # PowerShell then loads incompatible 7.x system modules (Microsoft docs).
        # Let the new shell construct its own edition's default module paths.
        for key in list(result):
            if key.casefold() == "psmodulepath":
                result.pop(key)
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        base = Path(bundle)
        result["PATH"] = os.pathsep.join(
            entry
            for entry in result.get("PATH", "").split(os.pathsep)
            if entry and not Path(entry).is_relative_to(base)
        )
    return result


@contextmanager
def external_process_scope() -> Iterator[None]:
    # PyInstaller's DLL directory is inherited by child processes. Native shells
    # and user programs must use Windows/their own libraries, not our Qt runtime.
    if os.name != "nt" or not getattr(sys, "frozen", False):
        yield
        return
    with _spawn_lock:
        kernel = ctypes.windll.kernel32
        kernel.GetDllDirectoryW.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p]
        kernel.GetDllDirectoryW.restype = ctypes.c_uint32
        kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
        kernel.SetDllDirectoryW.restype = ctypes.c_bool
        previous = ctypes.create_unicode_buffer(32768)
        kernel.GetDllDirectoryW(len(previous), previous)
        kernel.SetDllDirectoryW(None)
        try:
            yield
        finally:
            kernel.SetDllDirectoryW(previous.value or None)


def launch(args: list[str], **kwargs: Any) -> subprocess.Popen[Any]:
    kwargs["env"] = child_environment(kwargs.get("env"), args[0])
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    kwargs.setdefault("stdout", subprocess.DEVNULL)
    kwargs.setdefault("stderr", subprocess.DEVNULL)
    with external_process_scope():
        return subprocess.Popen(args, **kwargs)


FOLDERS = {
    "Downloads": "374DE290-123F-4565-9164-39C4925E467B",
    "Documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
    "Desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "Pictures": "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "Music": "4BD8D571-6D19-48D3-BE97-422220080E43",
    "Videos": "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
}


def known_folder(identifier: str) -> Path:
    guid = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID(identifier).bytes_le)
    result = ctypes.c_wchar_p()
    shell = ctypes.windll.shell32
    shell.SHGetKnownFolderPath.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    if shell.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(result)) != 0:
        raise OSError("Known Folder resolution failed")
    try:
        return Path(result.value or "")
    finally:
        ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(result, ctypes.c_void_p))


class WindowsPlatform(PlatformAdapter):
    def known_directories(self) -> dict[str, str]:
        result = {"home": str(Path.home())}
        for name, identifier in FOLDERS.items():
            result[name] = (
                str(known_folder(identifier)) if os.name == "nt" else str(Path.home() / name)
            )
        return result

    def is_admin(self) -> bool:
        return bool(ctypes.windll.shell32.IsUserAnAdmin()) if os.name == "nt" else False

    def system_directory(self) -> str:
        if os.name != "nt":
            return "/"
        buffer = ctypes.create_unicode_buffer(32768)
        if not ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, len(buffer)):
            raise OSError("No se pudo resolver el directorio de Windows")
        return buffer.value


def shell_executable(shell: str) -> str:
    name = {"cmd": "cmd.exe", "powershell": "powershell.exe", "pwsh": "pwsh.exe"}[shell]
    found = shutil.which(name)
    if not found:
        raise OSError(f"No se encontró {name}")
    return found


def hidden_run(
    args: list[str], *, timeout: float = 30, encoding: str | None = None
) -> subprocess.CompletedProcess[str]:
    process = launch(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=0x08000000 if os.name == "nt" else 0,
        encoding=encoding,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise
    return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
