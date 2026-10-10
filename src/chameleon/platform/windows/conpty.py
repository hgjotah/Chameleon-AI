import logging
import os
import signal
import socket
import threading
from pathlib import Path
from typing import Any

import psutil

from chameleon.platform.base import PtyBackend
from chameleon.platform.windows.system import child_environment, external_process_scope


class ConPtyBackend(PtyBackend):
    def __init__(
        self, argv: list[str], cwd: Path, env: dict[str, str], rows: int = 30, cols: int = 100
    ) -> None:
        if os.name != "nt":
            raise OSError("Chameleon Terminal requiere Windows 10 1809 o superior")
        from winpty import Backend, PtyProcess

        with external_process_scope():
            self.process: Any = PtyProcess.spawn(
                argv,
                cwd=str(cwd),
                env=child_environment(env, argv[0]),
                dimensions=(rows, cols),
                # pywinpty's spawn uses `backend or PYWINPTY_BACKEND`. Its zero
                # constant would permit an environment override; a string fixes it.
                backend=str(Backend.ConPTY),
            )
        self._lock = threading.Lock()
        self.closed = False

    @property
    def pid(self) -> int:
        return int(self.process.pid)

    def write(self, data: str) -> None:
        with self._lock:
            if not self.closed:
                self.process.write(data)

    def read(self) -> str:
        return str(self.process.read(32768))

    def resize(self, rows: int, cols: int) -> None:
        with self._lock:
            if not self.closed:
                self.process.setwinsize(max(2, rows), max(2, cols))

    def interrupt(self, break_event: bool = False) -> None:
        if break_event:
            try:
                os.kill(self.pid, signal.CTRL_BREAK_EVENT)
            except OSError:
                self.write("\x03")
        else:
            self.write("\x03")

    def close(self) -> None:
        with self._lock:
            if self.closed:
                return
            self.closed = True
        # Terminate children before the owning shell; avoids orphan REPLs/read deadlocks.
        try:
            shell = psutil.Process(self.pid)
            for child in reversed(shell.children(recursive=True)):
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            shell.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        # A child that already exited still owns the relay socket and native
        # reader. Release both, including blocked recv(), before Qt teardown.
        try:
            self.process.pty.cancel_io()
        except Exception:
            logging.getLogger("chameleon").debug("Native PTY reader already closed")
        try:
            self.process.fileobj.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.process.close(force=True)
        except Exception:
            logging.getLogger("chameleon").debug("PTY process already closed")
        finally:
            # PtyProcess.isalive() marks itself closed when the child exits;
            # its close() then skips the socket cleanup even though recv was open.
            self.process.fileobj.close()
            self.process._server.close()
