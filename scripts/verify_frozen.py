"""Ensure every bundled Chameleon code object matches the current source revision."""

import hashlib
import sys
import zipfile
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

repo = Path(__file__).resolve().parents[1]
for name in ("OpenConsole.exe", "conpty.dll", "winpty.dll"):
    assert (repo / "dist/Chameleon/_internal/winpty" / name).is_file(), (
        "Native PTY binary missing: " + name
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
assets = repo / "src/chameleon/assets"
for source in assets.rglob("*"):
    if source.is_file():
        relative = source.relative_to(assets)
        bundled_asset = repo / "dist/Chameleon/_internal/chameleon/assets" / relative
        assert bundled_asset.is_file() and bundled_asset.read_bytes() == source.read_bytes(), (
            "Frozen asset is stale: " + str(relative)
        )
print("PASS: bundled interface and shell assets match the current source")
if "--installer" in sys.argv:
    setup = CArchiveReader(str(repo / "dist" / "ChameleonSetup.exe"))
    assert setup.extract("chameleon.png") == (assets / "icons/chameleon.png").read_bytes(), "Bootstrap logo is stale"
    embedded = setup.extract("payload.zip")
    with (repo / "build" / "payload.zip").open("rb") as stream:
        expected_hash = hashlib.file_digest(stream, "sha256").digest()
    assert hashlib.sha256(embedded).digest() == expected_hash, "Installer payload is stale"
    del embedded
    with zipfile.ZipFile(repo / "build/payload.zip") as payload:
        for source in assets.rglob("*"):
            if source.is_file():
                name = "_internal/chameleon/assets/" + source.relative_to(assets).as_posix()
                assert payload.read(name) == source.read_bytes(), "Installer asset is stale: " + name
    print("PASS: standalone installer contains the exact current payload")
