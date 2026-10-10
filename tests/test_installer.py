import shutil
from pathlib import Path

import pytest

from chameleon.platform.windows.installer import (
    edit_profile,
    install,
    path_add,
    path_remove,
    remove_installation,
    uninstall_integration,
)


def test_path_preservation() -> None:
    existing = r"C:\Existing;%USERPROFILE%\Tools;C:\Other"
    entry = r"C:\Chameleon\bin"
    added = path_add(existing, entry)
    assert path_add(added, entry.upper()) == added
    assert path_remove(added, entry) == existing


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16"])
def test_profile_roundtrip(tmp_path: Path, encoding: str) -> None:
    path = tmp_path / "Profile.ps1"
    original = (
        "# Perfil español\r\nfunction prompt { 'personal> ' }\r\n$env:MiValor = 'niño'\r\n".encode(
            encoding
        )
    )
    path.write_bytes(original)
    module = tmp_path / "Chameleon.psm1"
    edit_profile(path, module)
    after = path.read_bytes()
    edit_profile(path, module)
    assert path.read_bytes() == after
    edit_profile(path, module, remove=True)
    assert path.read_bytes() == original
    assert list(tmp_path.glob("*.chameleon-backup-*"))


def test_malformed_profile_is_not_modified(tmp_path: Path) -> None:
    path = tmp_path / "Profile.ps1"
    original = b"# >>> Chameleon AI >>>\nuser content\n"
    path.write_bytes(original)
    with pytest.raises(ValueError):
        edit_profile(path, tmp_path / "module")
    assert path.read_bytes() == original


def test_install_repair_uninstall_temp(tmp_path: Path, shell_install: Path) -> None:
    payload = tmp_path / "payload"
    shutil.copytree(shell_install / "core", payload)
    profile = tmp_path / "user" / "profile.ps1"
    profile.parent.mkdir()
    original = b"# user's original profile\n"
    profile.write_bytes(original)
    root = tmp_path / "installation"
    install(root, payload, profiles=[profile], integrate=False)
    install(root, payload, profiles=[profile], integrate=False)
    (root / "bin" / "chameleon.cmd").unlink()
    install(root, payload, profiles=[profile], integrate=False)
    assert (root / "bin" / "chameleon.cmd").exists()
    uninstall_integration(root, integrate=False)
    assert profile.read_bytes() == original
    remove_installation(root)
    assert not root.exists()


def test_install_preflight_preserves_existing_payload(tmp_path: Path, shell_install: Path) -> None:
    payload = tmp_path / "payload"
    shutil.copytree(shell_install / "core", payload)
    root = tmp_path / "installed"
    install(root, payload, profiles=[], integrate=False)
    marker = root / "core" / "keep.txt"
    marker.write_text("existing installation")
    profile = tmp_path / "profile.ps1"
    original = b"# >>> Chameleon AI >>>\nuser content"
    profile.write_bytes(original)
    with pytest.raises(ValueError):
        install(root, payload, profiles=[profile], integrate=False)
    assert marker.read_text() == "existing installation"
    assert profile.read_bytes() == original


def test_failed_repair_rolls_back_payload_profiles_and_manifest(tmp_path: Path, shell_install: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from chameleon.platform.windows import installer

    payload = shell_install / "core"
    root = tmp_path / "rollback"
    profile = tmp_path / "profile.ps1"
    profile.write_bytes(b"# user profile\n")
    install(root, payload, profiles=[profile], integrate=False)
    marker = root / "core" / "original.txt"
    marker.write_text("original")
    before_profile = profile.read_bytes()
    before_manifest = (root / "install.json").read_bytes()
    before_module = (root / "bin" / "Chameleon.psm1").read_bytes()
    def fail(*args: object) -> None:
        raise OSError("Injected failure at final manifest commit")
    monkeypatch.setattr(installer, "write_manifest", fail)
    with pytest.raises(OSError, match="Injected"):
        install(root, payload, profiles=[profile], integrate=False)
    assert marker.read_text() == "original"
    assert profile.read_bytes() == before_profile
    assert (root / "install.json").read_bytes() == before_manifest
    assert (root / "bin" / "Chameleon.psm1").read_bytes() == before_module
