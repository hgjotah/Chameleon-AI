import os
import queue
import re
import shutil
import threading
import time
from pathlib import Path

import pytest

from chameleon.platform.windows.conpty import ConPtyBackend
from chameleon.terminal.integration import child_shell

pytestmark = pytest.mark.windows


def test_real_conpty_prompt_repl_resize_unicode(tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("Windows only")
    argv, env, token = child_shell("cmd", tmp_path / "state.json")
    backend = ConPtyBackend(argv, tmp_path, env)
    outputs: queue.Queue[str] = queue.Queue()

    def reader() -> None:
        try:
            while not backend.closed:
                outputs.put(backend.read())
        except (OSError, EOFError):
            return

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    output = ""

    def until(pattern: str, timeout: float = 10) -> str:
        nonlocal output
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                output += outputs.get(timeout=0.2)
            except queue.Empty:
                continue
            if pattern in output:
                return output
        raise AssertionError(f"Missing {pattern!r}: {output!r}")

    try:
        until("Chameleon-" + token)
        backend.resize(38, 120)
        backend.write("echo Niño español\r")
        until("Niño español")
        import sys

        backend.write('"' + sys.executable + '" -q\r')
        until(">>>")
        backend.write("print(17*19)\r")
        until("323")
        backend.write("exit()\r")
        time.sleep(0.2)
        if shutil.which("git"):
            backend.write("git --version\r")
            until("git version")
        if shutil.which("ssh"):
            backend.write("ssh -V\r")
            until("OpenSSH")
        backend.write("for /l %i in (1,1,1200) do @echo CONPTY_LINE_%i\r")
        until("CONPTY_LINE_1200")
        backend.write("ping -t 127.0.0.1\r")
        until("TTL=")
        output = ""
        backend.interrupt()
        until(str(tmp_path) + ">")
    finally:
        backend.close()
        thread.join(timeout=2)
    assert not thread.is_alive()
    assert re.search(r"\x1b\]0;Chameleon-" + token, output)
