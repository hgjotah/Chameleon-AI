"""Real registry, ACL and shortcuts with an isolated HKCU test key and temp APPDATA."""

import os
import shutil
import uuid
from pathlib import Path

import pytest

from chameleon.platform.windows.installer import (
    install,
    remove_installation,
    uninstall_integration,
    user_path,
)

pytestmark = pytest.mark.windows


def test_real_windows_install_repair_uninstall(
    tmp_path: Path, shell_install: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.name != "nt":
        pytest.skip("Windows only")
    import winreg

    actual_hkcu = winreg.HKEY_CURRENT_USER
    test_name = "Software\\ChameleonAI\\Tests\\" + uuid.uuid4().hex
    handle = winreg.CreateKey(actual_hkcu, test_name)
    environment = winreg.CreateKey(handle, "Environment")
    original_path = r"C:\Test Existing;%USERPROFILE%\Other"
    winreg.SetValueEx(environment, "Path", 0, winreg.REG_EXPAND_SZ, original_path)
    environment.Close()
    monkeypatch.setattr(winreg, "HKEY_CURRENT_USER", handle)
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    payload = tmp_path / "payload"
    shutil.copytree(shell_install / "core", payload)
    root = tmp_path / "Installed Chameleon"
    profile = tmp_path / "WindowsPowerShell" / "profile.ps1"
    profile.parent.mkdir()
    original_profile = b"# original profile\r\n"
    profile.write_bytes(original_profile)

    def delete_tree(parent: object, name: str) -> None:
        key = winreg.OpenKey(parent, name, 0, winreg.KEY_ALL_ACCESS)
        while True:
            try:
                child = winreg.EnumKey(key, 0)
            except OSError:
                break
            delete_tree(key, child)
        key.Close()
        winreg.DeleteKey(parent, name)

    try:
        install(root, payload, profiles=[profile])
        assert str(root / "bin") in user_path()
        shortcuts = (
            tmp_path
            / "AppData"
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Chameleon AI"
        )
        assert len(list(shortcuts.glob("*.lnk"))) == 3
        (root / "bin" / "chameleon.cmd").unlink()
        install(root, payload, profiles=[profile])
        assert (root / "bin" / "chameleon.cmd").exists()
        uninstall_integration(root)
        assert user_path() == original_path
        assert profile.read_bytes() == original_profile
        assert not shortcuts.exists()
        remove_installation(root)
        assert not root.exists()
    finally:
        handle.Close()
        if not test_name.startswith("Software\\ChameleonAI\\Tests\\"):
            raise RuntimeError("Unsafe registry cleanup")
        delete_tree(actual_hkcu, test_name)
