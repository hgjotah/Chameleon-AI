"""Self extracting distribution installer. Executes only its embedded release payload."""

import subprocess
import sys
import tempfile
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import messagebox, ttk


def main() -> int:
    window = tk.Tk()
    window.title("Chameleon AI")
    window.geometry("540x340")
    window.resizable(False, False)
    window.configure(bg="#0b110d")
    cancelled = False
    def cancel() -> None:
        nonlocal cancelled
        cancelled = True
    window.protocol("WM_DELETE_WINDOW", cancel)
    resource = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    if not getattr(sys, "frozen", False):
        resource = Path(__file__).resolve().parents[1] / "src/chameleon/assets/icons"
    logo = tk.PhotoImage(file=str(resource / "chameleon.png"))
    window.iconphoto(True, logo)
    mark = logo.subsample(max(1, logo.width() // 88))
    tk.Label(window, image=mark, bg="#0b110d").pack(pady=(22, 0))
    tk.Label(
        window, text="Chameleon", bg="#0b110d", fg="#b5cf97", font=("Segoe UI", 24, "bold")
    ).pack(pady=(8, 12))
    label = tk.Label(
        window,
        text="Preparing the local installer…",
        bg="#0b110d",
        fg="#e1eadb",
        font=("Segoe UI", 12),
    )
    label.pack()
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure("Chameleon.Horizontal.TProgressbar", background="#b5cf97", troughcolor="#253b2c", borderwidth=0, lightcolor="#b5cf97", darkcolor="#b5cf97")
    progress = ttk.Progressbar(window, style="Chameleon.Horizontal.TProgressbar", length=430, maximum=100)
    progress.pack(pady=18)
    tk.Label(window, text="LOCAL · PRIVATE · NO ACCOUNT", bg="#0b110d", fg="#8ca28b", font=("Segoe UI", 9)).pack()
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
                total = sum(info.file_size for info in bundle.infolist()) or 1
                completed = 0
                for info in bundle.infolist():
                    bundle.extract(info, target)
                    completed += info.file_size
                    percent = int(completed * 100 / total)
                    progress["value"] = percent
                    label.configure(text=f"Preparing the local installer… {percent}%")
                    window.update()
                    if cancelled:
                        return 130
            window.withdraw()
            executable = target / "ChameleonSetup.exe"
            process = subprocess.Popen(
                [str(executable), "--payload", str(target), *sys.argv[1:]], creationflags=0x08000000,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            while process.poll() is None:
                window.update()
                window.after(100)
            code = process.returncode
    except Exception as exc:
        messagebox.showerror("Chameleon Setup", f"Could not open Setup: {exc}")
    finally:
        window.destroy()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
