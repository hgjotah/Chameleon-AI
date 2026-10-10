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
