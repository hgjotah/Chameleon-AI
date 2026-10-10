import os
import shutil
import sys
from pathlib import Path

import pytest

from chameleon.core.config import asset_dir
from chameleon.core.context import Context


@pytest.fixture
def context(tmp_path: Path) -> Context:
    (tmp_path / "Downloads").mkdir()
    return Context(
        cwd=str(tmp_path),
        known_directories={"Downloads": str(tmp_path / "Downloads"), "home": str(tmp_path)},
    )


@pytest.fixture
def shell_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    if os.name != "nt":
        pytest.skip("Windows only")
    root = tmp_path / "Chameleon Test"
    (root / "bin").mkdir(parents=True)
    (root / "core").mkdir()
    launcher = Path(sys.executable).parent / "chameleon-core.exe"
    shutil.copy2(launcher, root / "core" / "ChameleonCore.exe")
    shutil.copy2(asset_dir() / "shell" / "chameleon.cmd", root / "bin" / "chameleon.cmd")
    shutil.copy2(asset_dir() / "shell" / "Chameleon.psm1", root / "bin" / "Chameleon.psm1")
    monkeypatch.setenv("CHAMELEON_HOME", str(root))
    monkeypatch.setenv("CHAMELEON_NONINTERACTIVE", "1")
    return root
