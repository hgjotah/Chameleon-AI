"""Small native console selectors; stdout stays reserved for the shell protocol."""

import ctypes
import os
import sys
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from typing import TextIO

ESC = "\x1b["
RESET = ESC + "0m"
SAGE = ESC + "38;2;182;216;161m"
MUTED = ESC + "38;2;154;175;157m"
ACTIVE = ESC + "48;2;39;65;45m" + SAGE + ESC + "1m"


@dataclass(frozen=True)
class Choice:
    label: str
    detail: str = ""


class Console:
    def __init__(self, stream: TextIO) -> None:
        self.stream = stream

    def write(self, text: str) -> None:
        self.stream.write(text)
        self.stream.flush()

    def size(self) -> tuple[int, int]:
        try:
            size = os.get_terminal_size(self.stream.fileno())
            return size.columns, size.lines
        except OSError:
            return 80, 24

    def key(self) -> str:
        import msvcrt

        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            return {
                "H": "up", "P": "down", "K": "up", "M": "down",
                "G": "home", "O": "end", "I": "pageup", "Q": "pagedown",
            }.get(msvcrt.getwch(), "")
        if key == "\x03":
            raise KeyboardInterrupt
        return {"\r": "enter", "\n": "enter", "\x1b": "escape"}.get(key, "")


@contextmanager
def open_console() -> Iterator[Console | None]:
    # PowerShell captures stdout to decode the plan. CONOUT$/CONIN$ still refer
    # to the real attached console, including ConPTY in Chameleon Terminal.
    if os.name != "nt" or os.environ.get("CHAMELEON_NONINTERACTIVE"):
        yield None
        return
    import msvcrt
    from ctypes import wintypes

    with ExitStack() as stack:
        try:
            stream = stack.enter_context(open("CONOUT$", "w", encoding="utf-8", newline=""))
            input_stream = stack.enter_context(open("CONIN$", "rb", buffering=0))
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.GetConsoleMode.restype = wintypes.BOOL
            kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.SetConsoleMode.restype = wintypes.BOOL
            handle = msvcrt.get_osfhandle(stream.fileno())
            input_handle = msvcrt.get_osfhandle(input_stream.fileno())
            output_mode, input_mode = wintypes.DWORD(), wintypes.DWORD()
            if not kernel.GetConsoleMode(handle, ctypes.byref(output_mode)):
                raise OSError("No output console is available")
            if not kernel.GetConsoleMode(
                input_handle, ctypes.byref(input_mode)
            ):
                raise OSError("No input console is available")
            # Keep raw input for the entire interaction, including redraws.
            # Otherwise Ctrl+C between getwch calls reaches the parent CMD and
            # triggers its "Terminate batch job?" prompt instead of cancellation.
            raw_mode = (input_mode.value | 0x0080) & ~(0x0001 | 0x0002 | 0x0004 | 0x0040 | 0x0200)
            if not kernel.SetConsoleMode(input_handle, raw_mode):
                raise OSError("Could not prepare the console keyboard")
            stack.callback(kernel.SetConsoleMode, input_handle, input_mode.value)
            if not kernel.SetConsoleMode(handle, output_mode.value | 0x0004):
                raise OSError("The console does not support VT sequences")
            stack.callback(kernel.SetConsoleMode, handle, output_mode.value)

            class CursorInfo(ctypes.Structure):
                _fields_ = [("size", wintypes.DWORD), ("visible", wintypes.BOOL)]

            kernel.GetConsoleCursorInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(CursorInfo)]
            kernel.GetConsoleCursorInfo.restype = wintypes.BOOL
            cursor = CursorInfo(25, True)
            kernel.GetConsoleCursorInfo(handle, ctypes.byref(cursor))
        except OSError:
            yield None
            return
        console = Console(stream)
        try:
            console.write(ESC + "?25l")
            yield console
        finally:
            with suppress(OSError):
                console.write(RESET + ESC + ("?25h" if cursor.visible else "?25l"))


def _fit(text: str, width: int) -> str:
    # Labels/metadata are display text, never terminal control sequences.
    text = "".join(c for c in text if c.isprintable())
    return text if len(text) <= width else text[: max(0, width - 1)] + "…"


def select(
    title: str, choices: list[Choice], selected: int = 0, details: str = ""
) -> int | None:
    if not choices:
        return None
    selected = max(0, min(selected, len(choices) - 1))
    with open_console() as console:
        if console is None:
            if details:
                print(details, file=sys.stderr)
            print(title, file=sys.stderr)
            for choice in choices:
                print(f"  {choice.label}  {choice.detail}".rstrip(), file=sys.stderr)
            print("No interactive console: nothing was selected or executed.", file=sys.stderr)
            return None
        if details:
            # A proposed command must not hide its own preview with ANSI/control
            # sequences. Display such characters as readable escapes.
            details = "".join(
                c if c.isprintable() or c in "\n\t" else c.encode("unicode_escape").decode("ascii")
                for c in details.replace("\r\n", "\n")
            )
            console.write("\r\n" + details.replace("\n", "\r\n") + "\r\n")
        console.write("\r\n")
        previous_lines = 0
        while True:
            columns, height = console.size()
            width = max(10, min(88, columns - 2))
            visible = min(len(choices), max(1, min(8, height - 7)))
            start = min(max(0, selected - visible // 2), len(choices) - visible)
            lines = [
                SAGE + "  " + _fit(title, width - 2) + RESET,
                MUTED + "  " + "─" * (width - 2) + RESET,
            ]
            for index in range(start, start + visible):
                item = choices[index]
                text = _fit(f"{item.label}  {item.detail}".rstrip(), width - 6)
                lines.append(
                    (ACTIVE if index == selected else MUTED)
                    + ("  › " if index == selected else "    ")
                    + text.ljust(width - 4) + RESET
                )
            lines.extend([
                MUTED + "  " + _fit(f"{selected + 1}/{len(choices)} · ↑/↓ move · Enter select · Esc cancel", width - 2) + RESET,
                "",
            ])
            if previous_lines:
                console.write(ESC + f"{previous_lines}F")
            count = max(previous_lines, len(lines))
            console.write("".join("\r" + ESC + "2K" + line + "\r\n" for line in lines + [""] * (count - len(lines))))
            previous_lines = count
            key = console.key()
            if key == "escape":
                return None
            if key == "enter":
                return selected
            if key == "up":
                selected = (selected - 1) % len(choices)
            elif key == "down":
                selected = (selected + 1) % len(choices)
            elif key == "home":
                selected = 0
            elif key == "end":
                selected = len(choices) - 1
            elif key == "pageup":
                selected = max(0, selected - visible)
            elif key == "pagedown":
                selected = min(len(choices) - 1, selected + visible)
