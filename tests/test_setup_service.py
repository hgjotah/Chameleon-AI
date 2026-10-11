from pathlib import Path

import pytest

from chameleon.setup import service
from chameleon.setup.service import InstallOptions, SetupService


def test_no_external_install_without_consent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []

    class OfflineProvider:
        def __init__(self, config: object) -> None:
            pass

        async def status(self) -> tuple[bool, bool]:
            return False, False

    monkeypatch.setattr(service, "OllamaProvider", OfflineProvider)
    monkeypatch.setattr(service, "ollama_executable", lambda: None)
    monkeypatch.setattr(
        service, "install_ollama", lambda progress: pytest.fail("Unconsented install")
    )
    ready = SetupService(tmp_path, tmp_path, events.append).configure_ai(InstallOptions(), {})
    assert not ready
    assert any("AI OFFLINE" in event for event in events)


def test_existing_model_is_probed_without_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    class ReadyProvider:
        def __init__(self, config: object) -> None:
            pass

        async def status(self) -> tuple[bool, bool]:
            return True, True

        async def probe(self) -> None:
            calls.append("probe")

        async def pull(self, progress: object) -> None:
            pytest.fail("Existing model was downloaded again")

    monkeypatch.setattr(service, "OllamaProvider", ReadyProvider)
    SetupService(tmp_path, tmp_path, lambda message: None).configure_ai(InstallOptions(), {})
    assert calls == ["probe"]


def test_failed_ai_probe_does_not_report_core_installation_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from chameleon.llm.base import ProviderError

    monkeypatch.setattr(service, "install", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "read_manifest", lambda root: {})
    monkeypatch.setattr(SetupService, "configure_policies", lambda *args: None)
    def fail(*args: object) -> None:
        raise ProviderError("Model timed out")
    monkeypatch.setattr(SetupService, "configure_ai", fail)
    events: list[str] = []
    result = SetupService(tmp_path, tmp_path, events.append).run(InstallOptions())
    assert "Terminal instalado correctamente" in result
    assert "necesita atención" in result
    assert any("IA pendiente" in event for event in events)


def test_fresh_ai_install_performs_every_dependency_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"binary": False, "online": False, "model": False}
    calls: list[str] = []
    class Provider:
        def __init__(self, config: object) -> None:
            pass
        async def status(self) -> tuple[bool, bool]:
            return state["online"], state["model"]
        async def pull(self, progress: object) -> None:
            calls.append("pull")
            state["model"] = True
        async def probe(self) -> None:
            assert state["online"] and state["model"]
            calls.append("probe")
    def install(progress: object) -> None:
        calls.append("install")
        state["binary"] = True
    async def start(progress: object) -> None:
        assert state["binary"]
        calls.append("start")
        state["online"] = True
    monkeypatch.setattr(service, "OllamaProvider", Provider)
    monkeypatch.setattr(service, "ollama_executable", lambda: "ollama.exe" if state["binary"] else None)
    monkeypatch.setattr(service, "install_ollama", install)
    monkeypatch.setattr(service, "ensure_server", start)
    monkeypatch.setattr(service, "write_manifest", lambda *args: None)
    manifest: dict = {}
    ready = SetupService(tmp_path, tmp_path, lambda _: None).configure_ai(InstallOptions(allow_ollama=True), manifest)
    assert ready and calls == ["install", "start", "pull", "probe"]
    assert manifest["installed_ollama"] and manifest["downloaded_model"] == "qwen3:4b-instruct"


def test_external_installer_success_without_binary_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class OfflineProvider:
        def __init__(self, config: object) -> None:
            pass
        async def status(self) -> tuple[bool, bool]:
            return False, False
    monkeypatch.setattr(service, "OllamaProvider", OfflineProvider)
    monkeypatch.setattr(service, "ollama_executable", lambda: None)
    monkeypatch.setattr(service, "install_ollama", lambda _: None)
    with pytest.raises(OSError, match="ollama.exe"):
        SetupService(tmp_path,tmp_path,lambda _: None).configure_ai(InstallOptions(allow_ollama=True),{})
