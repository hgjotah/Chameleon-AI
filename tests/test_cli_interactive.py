"""Real keyboard input through ConPTY and the installed-style shell wrappers."""

import os
import queue
import threading
import time
import uuid

import pytest

from chameleon.core.config import Config, save_config
from chameleon.platform.windows.conpty import ConPtyBackend
from chameleon.platform.windows.shells import ps_quote
from chameleon.platform.windows.system import shell_executable

pytestmark = pytest.mark.windows


@pytest.mark.parametrize("shell", ["cmd", "powershell", "pwsh"])
@pytest.mark.parametrize("approve", [True, False, None])
def test_try_real_keyboard_and_parent_state(shell_install, shell, approve):
    try:
        executable = shell_executable(shell)
    except OSError:
        pytest.skip("Shell not installed")
    config = Config()
    config.safety.mode = "full"
    save_config(config, shell_install)
    target = shell_install / "Destino Niño & literal"
    target.mkdir()
    environment = dict(os.environ)
    environment.pop("CHAMELEON_NONINTERACTIVE", None)
    environment["PATH"] = str(shell_install / "bin") + ";" + environment["PATH"]
    argv = [executable, "/d", "/q"] if shell == "cmd" else [executable, "-NoLogo", "-NoProfile"]
    backend = ConPtyBackend(argv, shell_install, environment, rows=30, cols=110)
    chunks = queue.Queue()
    output = ""

    def read():
        try:
            while not backend.closed:
                chunks.put(backend.read())
        except (OSError, EOFError):
            pass

    reader = threading.Thread(target=read, daemon=True)
    reader.start()

    def until(text):
        nonlocal output
        deadline = time.monotonic() + 30
        while text not in output:
            assert time.monotonic() < deadline, output[-6000:]
            try:
                output += chunks.get(timeout=0.1)
            except queue.Empty:
                pass

    try:
        if shell != "cmd":
            backend.write("Import-Module " + ps_quote(str(shell_install / "bin/Chameleon.psm1")) + "\r")
        request = 've a "' + str(target) + '"'
        invocation = "chameleon ai --try " + (request if shell == "cmd" else ps_quote(request))
        backend.write(invocation + "\r")
        until("Enter select")
        backend.write("\x1b[B\r" if approve else "\x03" if approve is None else "\r")
        marker = "RESULT_" + uuid.uuid4().hex + ":"
        backend.write(
            ('echo "' + marker + '%CD%"' if shell == "cmd" else "Write-Output ('" + marker + "'+(Get-Location).Path)") + "\r"
        )
        until(marker + str(target if approve else shell_install))
        if not approve:
            assert ("Cancelled." if approve is None else "The proposal was not executed") in output
        # Cancellation must not create even a pending execution artifact.
        assert not list((shell_install / "runtime/actions").glob("*.cmd"))
        assert not list((shell_install / "runtime/actions").glob("*.response"))
    finally:
        backend.close()
        reader.join(timeout=2)
