"""Self extracting distribution installer. Executes only its embedded release payload."""

import subprocess
import sys
import tempfile
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import messagebox


def main() -> int:
    window = tk.Tk()
    window.title("Chameleon AI")
    window.geometry("470x180")
    window.configure(bg="#080d0b")
    tk.Label(
        window, text="CHAMELEON AI", bg="#080d0b", fg="#51fa8b", font=("Segoe UI", 22, "bold")
    ).pack(pady=20)
    label = tk.Label(
        window,
        text="Preparando el instalador local…",
        bg="#080d0b",
        fg="#d8ecdf",
        font=("Segoe UI", 12),
    )
    label.pack()
    window.update()
    code = 1
    try:
        archive = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "payload.zip"
        with tempfile.TemporaryDirectory(prefix="chameleon-setup-") as directory:
            target = Path(directory)
            with zipfile.ZipFile(archive) as bundle:
                for info in bundle.infolist():
                    path = (target / info.filename).resolve()
                    if not path.is_relative_to(target.resolve()):
                        raise ValueError("Invalid payload path")
                bundle.extractall(target)
            window.withdraw()
            executable = target / "ChameleonSetup.exe"
            process = subprocess.Popen(
                [str(executable), "--payload", str(target), *sys.argv[1:]], creationflags=0x08000000
            )
            while process.poll() is None:
                window.update()
                window.after(100)
            code = process.returncode
    except Exception as exc:
        messagebox.showerror("Chameleon Setup", f"No se pudo abrir Setup: {exc}")
    finally:
        window.destroy()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
