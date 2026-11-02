import json
from contextlib import contextmanager

import httpx
import pytest

from chameleon import __version__, cli, cli_models, cli_ui
from chameleon.core.config import Config, load_config, save_config
from chameleon.core.schemas import Action, Plan
from chameleon.llm.base import ProviderError
from chameleon.safety.engine import Assessment, Risk


@pytest.fixture
def cli_home(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAMELEON_HOME", str(tmp_path))
    monkeypatch.setenv("CHAMELEON_NONINTERACTIVE", "1")
    config = Config()
    config.ai.model = "qwen2.5:0.5b"
    config.safety.mode = "full"
    save_config(config, tmp_path)
    return tmp_path


@pytest.mark.parametrize("args", [["ai", "--version"], ["--version"], ["version"]])
def test_version_never_needs_config_or_inference(args, monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_config", lambda *_: pytest.fail("Version loaded config"))
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    assert __version__ in captured.err and not captured.out


def test_model_and_help_never_infer_or_emit(cli_home, monkeypatch, capsys):
    before = (cli_home / "config/config.toml").read_bytes()
    monkeypatch.setattr(cli, "Engine", lambda *_args, **_kwargs: pytest.fail("Unexpected inference"))
    assert cli.main(["ai", "--model"]) == 0
    captured = capsys.readouterr()
    assert "qwen2.5:0.5b" in captured.err and not captured.out
    assert cli.main(["ai", "--help"]) == 0
    captured = capsys.readouterr()
    for flag in ("--version", "--model", "--models", "--changemodel", "--try", "--dry-run", "--force-model", "--show", "--debug"):
        assert flag in captured.err
    assert not captured.out and (cli_home / "config/config.toml").read_bytes() == before


def test_model_list_filters_remote_invalid_and_duplicates():
    import asyncio

    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"models": [
        {"name": "qwen2.5:0.5b"}, {"name": "qwen2.5:0.5b"},
        {"name": "custom:local"}, {"name": "bad\x1b[31m"},
        {"name": "test:cloud"}, {"name": "test-cloud"},
        {"name": "remote:latest", "remote_host": "https://example.test"}, None,
    ]}))
    assert asyncio.run(cli_models.installed_models(transport)) == ["qwen2.5:0.5b", "custom:local"]


@pytest.mark.parametrize("payload", [{}, {"models": None}, {"models": "wrong"}, [], None])
def test_model_list_rejects_malformed_response(payload):
    import asyncio

    with pytest.raises(ProviderError, match="No se cambió"):
        asyncio.run(cli_models.installed_models(httpx.MockTransport(lambda _: httpx.Response(200, json=payload))))


def mock_model_list(monkeypatch):
    async def tags():
        return ["qwen2.5:0.5b", "qwen3:4b-instruct"]

    async def metadata(self, client):
        assert self.config.model == "qwen3:4b-instruct"
        return {"model_info": {"verified": True}}

    monkeypatch.setattr(cli_models, "installed_models", tags)
    monkeypatch.setattr(cli_models.OllamaProvider, "local_metadata", metadata)


@pytest.mark.parametrize("interactive", [True, False])
def test_change_model_persists_only_model(cli_home, monkeypatch, interactive, capsys):
    mock_model_list(monkeypatch)

    def pick(title, choices, selected, details):
        assert selected == 0 and "ACTUAL" in choices[0].detail
        # A concurrent settings edit must not be reverted by selection.
        config, _ = load_config(cli_home)
        config.terminal.font_size = 22
        save_config(config, cli_home)
        return 1

    monkeypatch.setattr(cli_models, "select", pick)
    args = ["ai", "--changemodel"] + ([] if interactive else ["qwen3:4b-instruct"])
    assert cli.main(args) == 0
    result, _ = load_config(cli_home)
    assert result.ai.model == "qwen3:4b-instruct" and result.safety.mode == "full"
    assert result.terminal.font_size == (22 if interactive else 14)
    assert not capsys.readouterr().out


@pytest.mark.parametrize("mode", ["cancel", "missing", "offline", "verification"])
def test_change_failure_preserves_config(cli_home, monkeypatch, mode):
    mock_model_list(monkeypatch)
    before = (cli_home / "config/config.toml").read_bytes()
    monkeypatch.setattr(cli_models, "select", lambda *a, **kw: None)
    args = ["ai", "--changemodel"]
    if mode == "missing":
        args.append("not-downloaded:latest")
    elif mode == "offline":
        async def offline():
            raise ProviderError("Ollama desconectado")
        monkeypatch.setattr(cli_models, "installed_models", offline)
    elif mode == "verification":
        args.append("qwen3:4b-instruct")
        async def invalid(*a):
            raise ProviderError("No es local")
        monkeypatch.setattr(cli_models.OllamaProvider, "local_metadata", invalid)
    assert cli.main(args) == 1
    assert (cli_home / "config/config.toml").read_bytes() == before


def fake_plan(monkeypatch, target, risk=Risk.SAFE, forced=False):
    class Planner:
        def __init__(self, config, **kwargs):
            assert config.ai.prefer_model == forced

        async def plan(self, request, context):
            return (
                Plan(intent="execute", shell=context.shell, summary="Navegar", actions=[Action(kind="cd", path=str(target))]),
                Assessment(risk, "Revisión independiente"),
            )

    monkeypatch.setattr(cli, "Engine", Planner)


@pytest.mark.parametrize("answer", [None, 0, 1])
@pytest.mark.parametrize("risk", [Risk.SAFE, Risk.CONFIRM])
def test_try_requires_explicit_yes_before_emitting(cli_home, monkeypatch, capsys, answer, risk):
    fake_plan(monkeypatch, cli_home, risk)
    monkeypatch.setattr(cli, "ask", lambda *_: pytest.fail("Double confirmation"))

    def choose(title, options, selected, details):
        assert selected == 0 and options[0].label == "Cancelar"
        assert "Set-Location -LiteralPath" in details and str(cli_home) in details
        assert not list((cli_home / "runtime/actions").glob("*.cmd"))
        return answer

    monkeypatch.setattr(cli_ui, "select", choose)
    code = cli.main(["--emit", "powershell", "ai", "--try", "ve a una carpeta"])
    captured = capsys.readouterr()
    assert code == (0 if answer == 1 else 1)
    if answer == 1:
        assert json.loads(captured.out)["actions"][0]["path"] == str(cli_home)
    else:
        assert not captured.out


def test_try_noninteractive_full_access_cannot_emit(cli_home, monkeypatch, capsys):
    fake_plan(monkeypatch, cli_home)
    assert cli.main(["--emit", "cmd", "ai", "--try", "ve a una carpeta"]) == 1
    captured = capsys.readouterr()
    assert "cd /d" in captured.err and "Sin consola interactiva" in captured.err
    assert not captured.out and not list((cli_home / "runtime/actions").glob("*.cmd"))


def test_blocked_proposal_never_gets_execute_option(cli_home, monkeypatch):
    fake_plan(monkeypatch, cli_home, Risk.BLOCKED)
    monkeypatch.setattr(cli_ui, "select", lambda *a, **kw: pytest.fail("Blocked proposal offered"))
    assert cli.main(["ai", "--try", "ve a una carpeta"]) == 1


@pytest.mark.parametrize("flag", ["--model", "--force-model"])
def test_legacy_and_explicit_force_model(cli_home, monkeypatch, flag):
    fake_plan(monkeypatch, cli_home, forced=True)
    assert cli.main(["ai", flag, "--dry-run", "ve a una carpeta"]) == 0


@pytest.mark.parametrize("args", [
    ["ai", "--try", "--dry-run", "test"], ["ai", "--models", "test"],
    ["ai", "--version", "test"], ["ai", "--changemodel", "--try", "test"],
    ["ai", "--model", "--version"], ["ai", "--unknown"],
])
def test_invalid_option_combinations_fail_before_execution(args):
    with pytest.raises(SystemExit) as exc:
        cli.main(args)
    assert exc.value.code == 2


@pytest.mark.parametrize("keys,expected", [
    (["down", "enter"], 1), (["up", "enter"], 11),
    (["end", "home", "enter"], 0), (["pagedown", "enter"], 5),
    (["down", "escape"], None),
])
def test_selector_keyboard_paging_and_cancel(monkeypatch, keys, expected):
    output = []
    events = iter(keys)

    class FakeConsole:
        def write(self, text):
            output.append(text)

        def key(self):
            return next(events)

        def size(self):
            return 60, 12

    @contextmanager
    def console():
        yield FakeConsole()

    monkeypatch.setattr(cli_ui, "open_console", console)
    assert cli_ui.select("Modelo", [cli_ui.Choice(f"Modelo {i}") for i in range(12)], details="echo \x1b[2Jtexto") == expected
    assert "Enter elegir" in "".join(output)
    assert "\\x1b[2Jtexto" in "".join(output) and "\x1b[2Jtexto" not in "".join(output)
