import asyncio
import json

import httpx
import pytest

from chameleon.core.config import AIConfig, Config, SafetyConfig
from chameleon.core.context import Context
from chameleon.core.engine import Engine
from chameleon.llm.base import ProviderError
from chameleon.llm.ollama import OllamaProvider
from chameleon.safety.engine import Risk


def provider(outputs: list[str]) -> OllamaProvider:
    attempts = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen2"}})
        body = json.loads(request.content)
        assert "format" not in body and body["stream"]
        assert (
            "ONLY" in body["messages"][0]["content"] and "command" in body["messages"][0]["content"]
        )
        attempts.append(True)
        return httpx.Response(
            200,
            json={
                "model": "qwen2.5:0.5b",
                "eval_count": 5,
                "done_reason": "stop",
                "message": {"content": outputs[min(len(attempts) - 1, len(outputs) - 1)]},
            },
        )

    return OllamaProvider(AIConfig(model="qwen2.5:0.5b"), httpx.MockTransport(handle))


def test_only_command_is_returned() -> None:
    plan = asyncio.run(provider(["dir"]).plan("lista archivos", Context(cwd="C:/")))
    assert plan.summary == "dir" and plan.actions[0].command == "dir"
    assert plan.trace.calls == 1 and plan.trace.model == "qwen2.5:0.5b"


def test_native_translation_receives_runtime_facts_and_plural_file_context(tmp_path) -> None:
    downloads = tmp_path / "redirected downloads"
    downloads.mkdir()

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen2"}})
        body = json.loads(request.content)
        text = body["messages"][1]["content"]
        for fact in (
            "CustomBuild",
            "9.9",
            "Elevated administrator: True",
            str(downloads),
            "scripts",
            "read",
        ):
            assert fact in text
        assert "DO_NOT_SEND_THIS_SECRET" not in text
        return httpx.Response(200, json={"message": {"content": "dir"}})

    ctx = Context(
        cwd=str(tmp_path),
        os="Windows-11-CustomBuild",
        shell_version="9.9",
        admin=True,
        known_directories={"Downloads": str(downloads)},
        permissions={"read": True, "scripts": False},
    )
    plan = asyncio.run(
        OllamaProvider(AIConfig(), httpx.MockTransport(handle)).plan(
            "lista archivos en Downloads", ctx
        )
    )
    assert plan.actions[0].command == "dir"


def test_literal_cmd_environment_assignment_uses_parent_export() -> None:
    plan = asyncio.run(
        provider(['set "CHAMELEON_QA=alpha"']).plan(
            "establece variable CHAMELEON_QA a alpha", Context(cwd="C:/")
        )
    )
    assert (
        plan.actions[0].kind == "env"
        and plan.actions[0].name == "CHAMELEON_QA"
        and plan.actions[0].value == "alpha"
    )


def test_existing_script_is_not_replaced_with_generated_example(tmp_path) -> None:
    (tmp_path / "hello.cmd").write_text("@echo SCRIPT_OK", encoding="ascii")
    ctx = Context(
        cwd=str(tmp_path),
        permissions=dict.fromkeys(
            ("read", "write", "delete", "commands", "scripts", "network", "system"), True
        ),
    )
    plan = asyncio.run(
        provider(['powershell -Command "Write-Host Hello"', 'call "hello.cmd"']).plan(
            "ejecuta el script hello.cmd", ctx
        )
    )
    assert plan.actions[0].command == 'call "hello.cmd"' and plan.trace.calls == 2


@pytest.mark.parametrize(
    "bad",
    [
        "Hola, aquí tienes el comando: dir",
        "dir\ngracias",
        '{"command":"dir"}',
        "<think>...</think>dir",
    ],
)
def test_prose_or_wrappers_are_never_executed(bad: str) -> None:
    with pytest.raises(ProviderError):
        asyncio.run(provider([bad]).plan("lista", Context(cwd="C:/")))


def test_format_retry_can_recover_without_executing_bad_text() -> None:
    plan = asyncio.run(provider(["Hola, usa dir", "dir"]).plan("lista", Context(cwd="C:/")))
    assert plan.actions[0].command == "dir" and plan.trace.calls == 2


@pytest.mark.parametrize("wrapped", ["`dir`", "```cmd\ndir\n```"])
def test_single_command_delimiter_is_normalized(wrapped: str) -> None:
    plan = asyncio.run(provider([wrapped]).plan("lista", Context(cwd="C:/")))
    assert plan.actions[0].command == "dir"


def test_multiline_fence_does_not_smuggle_extra_commands() -> None:
    with pytest.raises(ProviderError):
        asyncio.run(
            provider(["```cmd\ndir\ndel important.txt\n```"]).plan("lista", Context(cwd="C:/"))
        )


def test_command_permissions_are_assessed_outside_model(tmp_path) -> None:
    (tmp_path / "file.txt").touch()
    cfg = Config(ai={"prefer_model": True}, safety=SafetyConfig(mode="read_only"))
    plan, risk = asyncio.run(
        Engine(cfg, provider(["del file.txt"])).plan("borra file.txt", Context(cwd=str(tmp_path)))
    )
    assert plan.actions[0].command == "del file.txt" and risk.level == Risk.BLOCKED
    cfg.safety.mode = "full"
    _, risk = asyncio.run(
        Engine(cfg, provider(["del file.txt"])).plan("borra file.txt", Context(cwd=str(tmp_path)))
    )
    assert risk.level == Risk.SAFE


def test_wrong_existing_target_is_retried_without_executing(tmp_path) -> None:
    (tmp_path / "a.txt").touch()
    (tmp_path / "b.txt").touch()
    cfg = Config(ai={"prefer_model": True})
    plan, risk = asyncio.run(
        Engine(cfg, provider(["del b.txt", "del a.txt"])).plan(
            "borra a.txt", Context(cwd=str(tmp_path))
        )
    )
    assert plan.actions[0].command == "del a.txt" and plan.trace.calls == 2
    assert (
        risk.level == Risk.CONFIRM
        and (tmp_path / "a.txt").exists()
        and (tmp_path / "b.txt").exists()
    )
