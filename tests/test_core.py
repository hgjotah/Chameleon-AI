import asyncio
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from chameleon.core.config import Config, load_config, save_config
from chameleon.core.context import Context
from chameleon.core.engine import Engine
from chameleon.core.intents import is_real_command, local_plan
from chameleon.core.privacy import redact
from chameleon.core.schemas import Action, Plan
from chameleon.llm.base import ProviderError
from chameleon.llm.ollama import OllamaProvider
from chameleon.platform.windows.shells import cmd_quote, ps_quote
from chameleon.safety.engine import Risk, RiskEngine


@pytest.mark.parametrize(
    "text,kind",
    [
        ("ve a Downloads", "cd"),
        ("Downloads", "cd"),
        ("muéstrame los archivos", "list"),
        ("encuentra todos los PDF", "find"),
        ("lista los pdf", "list"),
        ("go to Downloads", "cd"),
        ("sube una carpeta", "cd"),
    ],
)
def test_local_parser(context: Context, text: str, kind: str) -> None:
    plan = local_plan(text, context)
    assert plan and plan.actions[0].kind == kind


def test_missing_and_ambiguous(context: Context) -> None:
    plan = local_plan("ve a InventedFolder", context)
    assert plan and plan.intent == "clarify" and not plan.actions
    context.entries = ["old.txt", "old2.txt", "backup-old.zip"]
    plan = local_plan("borra el archivo viejo", context)
    assert plan and plan.intent == "clarify" and len(plan.choices) == 3


@pytest.mark.parametrize(
    "line", ["dir", "git status", "python", "ping 8.8.8.8", "echo hola & dir", "set VAR=hello"]
)
def test_real_commands(context: Context, line: str) -> None:
    assert is_real_command(line, context)


def test_ps_aliases(context: Context) -> None:
    context.shell = "powershell"
    assert is_real_command("MyAlias anything", context, {"myalias"})
    assert is_real_command("$a = 2", context)
    assert not is_real_command("busca archivos python mayores de 1 MB", context)


@pytest.mark.parametrize(
    "value",
    [
        r"C:\Users\Test User",
        r"C:\Prueba con espacios",
        r"C:\Español\Niño",
        "a'b",
        "a%b",
        "a!b",
        "a&b",
        "a|b",
        "a<b",
        "a>b",
        "a^b",
        "a(b)",
    ],
)
def test_quoting(value: str) -> None:
    assert cmd_quote(value).startswith('"')
    assert cmd_quote(value).endswith('"')
    if "%" in value:
        assert "%%" in cmd_quote(value)
    assert ps_quote(value) == "'" + value.replace("'", "''") + "'"


@pytest.mark.parametrize("value", ['a"b', "a\nb", "a\x00b"])
def test_cmd_rejects_invalid(value: str) -> None:
    with pytest.raises(ValueError):
        cmd_quote(value)


@pytest.mark.parametrize(
    "command,risk",
    [
        ("dir", Risk.SAFE),
        ("git status", Risk.SAFE),
        ("taskkill /pid 123", Risk.CONFIRM),
        ('del "old.txt"', Risk.CONFIRM),
        (r"rmdir /s /q C:\Windows", Risk.BLOCKED),
        ("del /s C:\\", Risk.BLOCKED),
        ("format C:", Risk.BLOCKED),
        ("diskpart /s script.txt", Risk.BLOCKED),
        ("powershell -EncodedCommand x", Risk.BLOCKED),
        ('python -c "danger"', Risk.BLOCKED),
        ("dir > output.txt", Risk.CONFIRM),
        ("dir & shutdown /s", Risk.CONFIRM),
        ("unknown-program", Risk.BLOCKED),
        (r"C:\Temp\ipconfig.exe", Risk.BLOCKED),
        ("git diff --output=important.txt", Risk.CONFIRM),
        ("del %SystemRoot%", Risk.BLOCKED),
    ],
)
def test_risk(command: str, risk: Risk) -> None:
    assert RiskEngine().command(command).level == risk


def test_typed_delete_system() -> None:
    action = Action(kind="delete", path=r"C:\Windows\System32", recursive=True)
    assert RiskEngine().action(action, Path("C:/")).level == Risk.BLOCKED


def test_relative_destructive_paths_respect_execution_cwd() -> None:
    risk = RiskEngine()
    assert risk.command("rmdir /s /q ..", Path(r"C:\Windows\System32")).level == Risk.BLOCKED
    assert risk.command('del /s /q "."', Path("C:/")).level == Risk.BLOCKED
    assert risk.command('del "old.txt"', Path(r"C:\Users\Test")).level == Risk.CONFIRM
    plan = Plan(
        intent="execute",
        shell="cmd",
        summary="blocked",
        actions=[
            Action(kind="cd", path=r"C:\Windows"),
            Action(kind="command", command="rmdir /s /q ."),
        ],
    )
    assert risk.assess(plan, Path(r"C:\Users\Test")).level == Risk.BLOCKED
    plan.actions[0] = Action(kind="command", command=r"cd %WINDIR%")
    assert risk.assess(plan, Path(r"C:\Users\Test")).level == Risk.BLOCKED


def test_protected_system_directory_on_another_drive() -> None:
    assert (
        RiskEngine(r"D:\Windows")
        .action(Action(kind="delete", path=r"D:\Windows\System32", recursive=True), Path("D:/"))
        .level
        == Risk.BLOCKED
    )


def test_schema_rejects_model_text() -> None:
    with pytest.raises(ValidationError):
        Plan.model_validate(
            {"intent": "execute", "shell": "cmd", "summary": "danger", "commands": ["dir"]}
        )
    with pytest.raises(ValidationError):
        Action(kind="command", command="dir\nformat C:")


def test_provider_schema_and_retry(context: Context) -> None:
    calls = []

    def mock(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen3"}})
        data = json.loads(request.content)
        calls.append(data)
        assert data["format"]["type"] == "object"
        assert "actions" in data["format"]["required"]
        assert data["format"]["properties"]["shell"]["const"] == context.shell
        assert request.url.host == "127.0.0.1"
        content = (
            "bad json"
            if len(calls) == 1
            else Plan(
                intent="execute",
                shell="cmd",
                summary="Listar",
                actions=[Action(kind="list", path=context.cwd)],
            ).model_dump_json()
        )
        return httpx.Response(200, json={"message": {"content": content}})

    provider = OllamaProvider(Config().ai, httpx.MockTransport(mock))
    plan = asyncio.run(provider.plan("list", context))
    assert plan.intent == "execute" and len(calls) == 2


def test_provider_invalid_fails(context: Context) -> None:
    provider = OllamaProvider(
        Config().ai,
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"model_info": {"general.architecture": "qwen3"}}
                if request.url.path == "/api/show"
                else {"message": {"content": "{}"}},
            )
        ),
    )
    with pytest.raises(ProviderError):
        asyncio.run(provider.plan("danger", context))


def test_local_rules_work_offline(context: Context) -> None:
    config = Config()
    config.ai.enabled = False
    plan, assessment = asyncio.run(Engine(config).plan("Downloads", context))
    assert plan.actions[0].kind == "cd" and assessment.level == Risk.SAFE


def test_config_recovery(tmp_path: Path) -> None:
    config = Config()
    assert not config.privacy.save_ai_history
    save_config(config, tmp_path)
    assert load_config(tmp_path)[0] == config
    (tmp_path / "config" / "config.toml").write_text("bad [", encoding="utf-8")
    restored, warning = load_config(tmp_path)
    assert warning and restored == Config()
    assert list((tmp_path / "config").glob("*.broken-*.toml"))


def test_redaction() -> None:
    text = "token=abc password=hunter2\nAuthorization: Bearer abc\n-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----"
    result = redact(text)
    assert "hunter2" not in result and "Bearer abc" not in result and "\nabc\n" not in result


def test_model_context_strips_control_data(context: Context) -> None:
    context.observed_output = "\x1b[32m" + "old output " * 1000 + "\x1b[0m\nniño token=secret"
    context.executables = {"git": "verified git", "ssh": "verified ssh"}
    payload = context.model_payload("git status")
    assert len(payload["observed_output"]) <= 600
    assert "\x1b" not in payload["observed_output"] and "secret" not in payload["observed_output"]
    assert payload["executables"] == {"git": "verified git"}


def test_cloud_alias_blocked_before_prompt(context: Context) -> None:
    calls: list[str] = []

    def mock(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(
            200, json={"remote_host": "https://ollama.com", "remote_model": "cloud-model"}
        )

    with pytest.raises(ProviderError):
        asyncio.run(
            OllamaProvider(Config().ai, httpx.MockTransport(mock)).plan("private request", context)
        )
    assert calls == ["/api/show"]


def test_cloud_config_rejected() -> None:
    with pytest.raises(ValueError):
        Config().ai.model = "gemma4:cloud"
