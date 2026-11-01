import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dist = root / "dist"
if "--final" not in sys.argv:
    with zipfile.ZipFile(
        root / "build" / "payload.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for path in sorted((dist / "Chameleon").rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(dist / "Chameleon"))
else:
    try:
        source_files = subprocess.check_output(
            ["git", "ls-files"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).splitlines()
    except (OSError, subprocess.CalledProcessError):
        source_files = []
    if not source_files:
        source_files = [p.name for p in root.iterdir() if p.is_file()]
        for directory in ("src", "tests", "scripts", "installer", "docs", ".github"):
            source_files.extend(
                str(p.relative_to(root))
                for p in (root / directory).rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and p.suffix not in (".pyc", ".log", ".spec")
            )
        source_files.append("installer/chameleon.spec")
    with zipfile.ZipFile(
        dist / "ChameleonAI-0.5.1-source.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for name in source_files:
            path = root / name
            if path.is_file():
                archive.write(path, name)
    with zipfile.ZipFile(
        dist / "ChameleonAI-0.5.1-windows-x64.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for path in sorted((dist / "Chameleon").rglob("*")):
            if path.is_file():
                archive.write(path, "Chameleon/" + str(path.relative_to(dist / "Chameleon")))
        for name in (
            "README.md",
            "ARCHITECTURE.md",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "LICENSE",
            "THIRD_PARTY_NOTICES.md",
            *(str(p.relative_to(root)) for p in sorted((root / "docs").glob("*.md"))),
        ):
            archive.write(root / name, name)
        archive.writestr(
            "LEEME-PORTABLE.txt",
            "Chameleon AI 0.5.1\n\nConserva la carpeta Chameleon completa.\nPara abrir el terminal: Chameleon\\ChameleonTerminal.exe\nPara instalar la integración CMD/PowerShell: Chameleon\\ChameleonSetup.exe\nSettings: Chameleon\\ChameleonSetup.exe settings\nOllama y qwen3:4b-instruct deben estar instalados para las consultas de IA.\nConsulta README.md y docs/INSTALLATION.md.\n",
        )
    sums = {}
    for path in dist.iterdir():
        if path.is_file() and path.name != "SHA256SUMS.json":
            with path.open("rb") as stream:
                sums[path.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    (dist / "SHA256SUMS.json").write_text(json.dumps(sums, indent=2), encoding="utf-8")
