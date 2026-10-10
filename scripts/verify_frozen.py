"""Ensure every bundled Chameleon code object matches the current source revision."""

import hashlib
import sys
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

repo = Path(__file__).resolve().parents[1]
assert (repo / "dist/Chameleon/_internal/winpty/OpenConsole.exe").is_file(), (
    "Native ConPTY host missing"
)
archive = CArchiveReader(str(repo / "dist" / "Chameleon" / "ChameleonCore.exe"))
pyz = archive.open_embedded_archive("PYZ.pyz")
checked = 0
for name in pyz.toc:
    if name != "chameleon" and not name.startswith("chameleon."):
        continue
    path = repo / "src" / Path(*name.split("."))
    source = path.with_suffix(".py") if path.with_suffix(".py").exists() else path / "__init__.py"
    bundled = pyz.extract(name)
    expected = compile(source.read_text(encoding="utf-8"), bundled.co_filename, "exec", optimize=0)
    if bundled != expected:
        raise RuntimeError("Frozen code is stale: " + name)
    checked += 1
print(f"PASS: {checked} bundled code modules match the current source")
if "--installer" in sys.argv:
    setup = CArchiveReader(str(repo / "dist" / "ChameleonSetup.exe"))
    embedded = setup.extract("payload.zip")
    with (repo / "build" / "payload.zip").open("rb") as stream:
        expected_hash = hashlib.file_digest(stream, "sha256").digest()
    assert hashlib.sha256(embedded).digest() == expected_hash, "Installer payload is stale"
    print("PASS: standalone installer contains the exact current payload")
