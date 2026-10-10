import os
import queue
import re
import threading
import time
from pathlib import Path

import pytest

from chameleon.platform.windows.conpty import ConPtyBackend
from chameleon.platform.windows.shells import ps_quote
from chameleon.platform.windows.system import shell_executable


@pytest.mark.windows
@pytest.mark.parametrize("shell", ["cmd", "powershell", "pwsh"])
def test_native_wrapper_creates_file_after_real_confirmation(shell_install: Path, tmp_path: Path, shell: str) -> None:
    environment = dict(os.environ)
    environment.pop("CHAMELEON_NONINTERACTIVE", None)
    try:
        executable = shell_executable(shell)
    except OSError:
        pytest.skip("Optional PowerShell 7 is not installed")
    argv = [executable, "/d", "/q", "/v:off"] if shell == "cmd" else [executable, "-NoLogo", "-NoProfile", "-NoExit"]
    backend = ConPtyBackend(argv, tmp_path, environment)
    chunks: queue.Queue[str] = queue.Queue()
    def read() -> None:
        try:
            while not backend.closed:
                chunk = backend.read()
                if "\x1b[c" in chunk or "\x1b[0c" in chunk:
                    backend.write("\x1b[?1;2c")
                if "\x1b[6n" in chunk:
                    backend.write("\x1b[1;1R")
                chunks.put(chunk)
        except Exception:
            return
    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    output = ""
    def until(text: str) -> None:
        nonlocal output
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                output += chunks.get(timeout=0.1)
            except queue.Empty:
                continue
            plain = re.sub(r"\x1b\][^\x07]*?(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]", "", output)
            if text in plain:
                return
        raise AssertionError(f"Missing {text}: {output!r}")
    try:
        until(">")
        backend.write("echo READY_TEST_CREATION\r")
        until("\r\nREADY_TEST_CREATION\r\n")
        phrase = 'crea un archivo llamado "archivo Niño.txt" con contenido "Hola, acción & echo LITERAL"'
        if shell == "cmd":
            command = 'call "' + str(shell_install / "bin/chameleon.cmd") + '" ai ' + phrase
        else:
            command = "Import-Module " + ps_quote(str(shell_install / "bin/Chameleon.psm1")) + "; chameleon ai " + ps_quote(phrase)
        backend.write(command + "\r")
        until("¿Ejecutar?")
        assert not (tmp_path / "archivo Niño.txt").exists()
        backend.write("s\r")
        until("Archivo creado:")
        assert (tmp_path / "archivo Niño.txt").read_text(encoding="utf-8") == "Hola, acción & echo LITERAL"
        if shell != "cmd":
            output = ""
            backend.write("chameleon ai " + ps_quote('lee "archivo Niño.txt"') + "\r")
            until("\r\nHola, acción & echo LITERAL\r\n")
    finally:
        backend.close()
        thread.join(timeout=3)
    assert not thread.is_alive()
