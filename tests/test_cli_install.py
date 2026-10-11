import asyncio
import sys
from pathlib import Path

import pytest

from chameleon.cli import main
from chameleon.setup import service


def test_frozen_cli_update_allows_services_async_model_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAMELEON_HOME", str(tmp_path / "user-install"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    payload = tmp_path / "release"
    calls = []

    class TestService:
        def __init__(self, root, actual_payload, progress):
            assert root == tmp_path / "user-install" and actual_payload == payload
            self.progress = progress

        def run(self, options):
            # The real service uses asyncio.run for Ollama status/probe. It
            # must not run inside the CLI's already-active event loop.
            asyncio.run(asyncio.sleep(0))
            assert not options.pull_model and not options.allow_ollama
            calls.append(options)
            return "Instalación lista."

    monkeypatch.setattr(service, "SetupService", TestService)
    assert main(["setup", "--install", "--payload", str(payload)]) == 0
    assert len(calls) == 1


def test_source_cli_install_explains_standalone_requirement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setenv("CHAMELEON_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert main(["setup", "--install"]) == 1
    assert "ejecutable independiente" in capsys.readouterr().err


def test_frozen_cli_explicit_dependency_install_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAMELEON_HOME",str(tmp_path))
    monkeypatch.setattr(sys,"frozen",True,raising=False)
    class TestService:
        def __init__(self,*args):
            pass
        def run(self,options):
            assert options.allow_ollama and options.pull_model
            return "Terminal instalado correctamente. La IA necesita atención."
    monkeypatch.setattr(service,"SetupService",TestService)
    assert main(["setup","--install","--install-ollama"])==3
