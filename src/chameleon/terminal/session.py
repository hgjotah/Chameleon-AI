import asyncio
import json
import logging
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from chameleon.core.config import Config, data_dir
from chameleon.core.context import Context, build_context
from chameleon.core.engine import Engine
from chameleon.core.intents import is_real_command
from chameleon.core.privacy import redact
from chameleon.core.schemas import Plan
from chameleon.llm.ollama import OllamaProvider
from chameleon.platform.windows.conpty import ConPtyBackend
from chameleon.platform.windows.protocol import emit_cmd
from chameleon.platform.windows.shells import PowerShellAdapter, cmd_quote
from chameleon.safety.engine import Assessment
from chameleon.terminal.integration import child_shell


class TerminalSession(QObject):
    output = Signal(str)
    plan_ready = Signal(object, object)
    failed = Signal(str)
    status = Signal(str)
    exited = Signal()
    location = Signal(str)

    def __init__(self, config: Config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.root = data_dir()
        self.cwd = Path(config.terminal.start_directory or Path.home()).resolve()
        if not self.cwd.is_dir():
            self.cwd = Path.home()
        self.recent: list[str] = []
        self.tail = ""
        self.aliases: set[str] = set()
        self.shell_version = "unknown"
        self.at_prompt = False
        self.raw_mode = False
        self.busy = False
        self.pending: Plan | None = None
        self.pending_command: str | None = None
        self.last_request = ""
        self.closed = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[Any] | None = None
        self.cancel_requested = threading.Event()
        self._health_lock = threading.Lock()
        self._hidden_echo = ""
        self._suppress_echo = False
        state_dir = self.root / "runtime" / "terminal"
        state_dir.mkdir(parents=True, exist_ok=True)
        import secrets

        self.state_file = state_dir / (secrets.token_hex(16) + ".json")
        argv, env, self.token = child_shell(config.terminal.shell, self.state_file)
        self.backend = ConPtyBackend(argv, self.cwd, env)
        self.reader = threading.Thread(target=self._read, daemon=True, name="ConPTY reader")
        self.health_timer = QTimer(self)
        self.health_timer.setInterval(20000)
        self.health_timer.timeout.connect(
            lambda: threading.Thread(target=self.check_ai, daemon=True).start()
        )

    def start(self) -> None:
        if self.closed:
            return
        if not self.reader.is_alive():
            self.reader.start()
        if self.config.general.startup_checks:
            threading.Thread(target=self.check_ai, daemon=True).start()
            self.health_timer.start()
        else:
            self.status.emit("AI ENABLED" if self.config.ai.enabled else "AI DISABLED")

    def update_config(self, config: Config) -> None:
        actual_shell = self.config.terminal.shell
        self.config = config.model_copy(deep=True)
        self.config.terminal.shell = actual_shell

    def _read(self) -> None:
        try:
            while not self.closed:
                chunk = self.backend.read()
                if not chunk:
                    continue
                if self._suppress_echo:
                    self._hidden_echo += chunk
                    # ConPTY redraw uses cursor-next-line rather than CRLF on some hosts.
                    import re

                    match = re.search(r"\r?\n|\x1b\[\d*E", self._hidden_echo)
                    if not match and len(self._hidden_echo) < 16384:
                        continue
                    if match:
                        prefix = self._hidden_echo[: match.end()]
                        # Retain native cursor/screen state while hiding only echo text.
                        controls = "".join(re.findall(r"\x1b\[[0-?]*[ -/]*[@-~]|\r|\n", prefix))
                        chunk = controls + self._hidden_echo[match.end() :]
                    else:
                        chunk = self._hidden_echo
                    self._hidden_echo = ""
                    self._suppress_echo = False
                self.tail = (self.tail + chunk)[-4096:]
                self.output.emit(chunk)
        except Exception as exc:
            logging.getLogger("chameleon").info("Shell reader ended: %s", type(exc).__name__)
            if not self.closed:
                self.closed = True
                self.exited.emit()

    def prompt(self, token: str, cwd: str) -> bool:
        if token != self.token or self.closed:
            return False
        if self.busy and self.pending_command is None:
            # ConPTY may replay the window title on focus changes (e.g. a
            # confirmation dialog). It is not a new editable shell prompt.
            return False
        candidate = Path(cwd)
        # CMD also appends the running command to its window title. That is not
        # a prompt acknowledgement and must never enable AI inside a REPL.
        if not candidate.is_dir():
            return False
        self.cwd = candidate
        self.location.emit(str(candidate))
        self.at_prompt = not self.raw_mode
        if self.pending_command is not None:
            command = self.pending_command
            self.pending_command = None
            self.at_prompt = False
            self.busy = False
            self._suppress_echo = not self.config.ai.show_generated_commands
            self.backend.write(command + "\r")
            threading.Thread(target=self.check_ai, daemon=True).start()
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.aliases = {str(s).casefold() for s in state.get("aliases", [])}
            self.shell_version = state.get("shell_version", "unknown")
        except (OSError, ValueError):
            self.aliases = set()
        return self.pending_command is None and self.at_prompt

    def check_ai(self) -> None:
        if self.busy or self.closed or not self._health_lock.acquire(blocking=False):
            return
        try:
            if not self.config.ai.enabled:
                self.status.emit("AI DISABLED")
                return
            online, model = asyncio.run(OllamaProvider(self.config.ai).status())
            self.status.emit("AI LOCAL" if online and model else "AI OFFLINE")
        finally:
            self._health_lock.release()

    def data(self, text: str) -> None:
        if self.closed:
            return
        if self.busy:
            if "\x03" in text:
                self.cancel()
            return
        if "\x03" in text:
            self.at_prompt = False
        self.backend.write(text)

    def submit(self, line: str) -> None:
        if self.busy or self.closed:
            return
        context = Context(cwd=str(self.cwd), shell=self.config.terminal.shell)
        if self.raw_mode or not self.at_prompt or is_real_command(line, context, self.aliases):
            self.at_prompt = False
            self.backend.write("\r")
            return
        context = build_context(self.cwd, self.config.terminal.shell, self.recent)
        self.busy = True
        self.cancel_requested.clear()
        self.last_request = line
        self.at_prompt = False
        self.status.emit("PROCESSING")
        context.shell_version = self.shell_version
        context.observed_output = redact(self.tail)[-2000:]

        def worker() -> None:
            loop = asyncio.new_event_loop()
            self._loop = loop
            try:
                self._task = loop.create_task(Engine(self.config).plan(line, context))
                if self.cancel_requested.is_set():
                    self._task.cancel()
                plan, assessment = loop.run_until_complete(self._task)
                if not self.closed and not self.cancel_requested.is_set():
                    self.plan_ready.emit(plan, assessment)
                elif not self.closed:
                    self.failed.emit("Cancelado.")
            except asyncio.CancelledError:
                self.failed.emit("Cancelado.")
            except Exception as exc:
                logging.getLogger("chameleon").info("Inference failed: %s", type(exc).__name__)
                self.failed.emit(
                    str(exc)
                    if isinstance(exc, (ValueError, OSError, RuntimeError))
                    else "Error de IA local. Ejecuta chameleon doctor."
                )
            finally:
                self._loop = None
                self._task = None
                loop.close()

        threading.Thread(target=worker, daemon=True, name="Local AI").start()

    def cancel(self) -> None:
        self.cancel_requested.set()
        self.pending_command = None
        loop, task = self._loop, self._task
        if loop and task:
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                logging.getLogger("chameleon").debug(
                    "Inference loop already closed during cancellation"
                )
        if self.busy and task is None and not self.closed:
            self.reset_prompt()

    def reset_prompt(self) -> None:
        if self.closed:
            return
        self.busy = False
        self.at_prompt = False
        self.pending_command = None
        self.backend.write("\x03")
        threading.Thread(target=self.check_ai, daemon=True).start()

    def execute(self, plan: Plan, assessment: Assessment) -> None:
        if self.closed:
            return
        self.recent = (self.recent + [redact(plan.summary)])[-6:]
        if self.config.privacy.save_ai_history:
            history = self.root / "history"
            history.mkdir(exist_ok=True)
            with (history / "ai.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        {"request": redact(self.last_request), "summary": redact(plan.summary)},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        if self.config.terminal.shell == "cmd":
            token = emit_cmd(plan, self.cwd, self.root)
            quoted = cmd_quote(
                str(self.root / "runtime" / "actions" / (token + ".cmd")), batch=False
            )
            command = "@" + quoted + " & del " + quoted + " >nul 2>&1"
        else:
            commands = [PowerShellAdapter().render(a, self.cwd) for a in plan.actions]
            command = "; ".join(commands)
        # Cancel the shell's editable line and wait for its real prompt acknowledgement.
        # Combining ESC with injected text can be decoded as an Alt key by ConPTY.
        self.pending_command = command
        self.backend.write("\x03")
        QTimer.singleShot(5000, self._pending_timeout)
        threading.Thread(target=self.check_ai, daemon=True).start()

    def _pending_timeout(self) -> None:
        if self.pending_command is not None and not self.closed:
            self.pending_command = None
            self.failed.emit("El shell no respondió al cambio de línea. No se ejecutó la acción. Pulsa Ctrl+C y vuelve a intentarlo.")

    def close(self) -> None:
        self.closed = True
        self.health_timer.stop()
        self.cancel()
        self.backend.close()
        if self.reader.is_alive():
            self.reader.join(timeout=2)
        self.state_file.unlink(missing_ok=True)
