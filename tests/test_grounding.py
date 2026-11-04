import asyncio
import json
from pathlib import Path

import httpx
import pytest

from chameleon.core.config import Config
from chameleon.core.context import Context
from chameleon.core.engine import Engine
from chameleon.core.inspection import inspect_action
from chameleon.core.intents import local_plan, resolve_reference
from chameleon.core.schemas import Action, Plan
from chameleon.llm.base import ProviderError
from chameleon.llm.ollama import OllamaProvider
from chameleon.safety.engine import Risk


@pytest.mark.parametrize(
    "phrase",
    [
        "borra un archivo en Downloads llamado Prueba.txt",
        "borra el archivo Prueba.txt en Downloads",
        "elimina el archivo llamado Prueba.txt en Downloads",
        "borra un archivo en Downloads llamado Prueba",
        "borra Prueba en Descargas",
        "delete a file in Downloads called Prueba.txt",
        'borra el archivo "Prueba.txt" en Downloads',
    ],
)
def test_reported_delete_phrase_resolves_verified_target(tmp_path: Path, phrase: str) -> None:
    downloads = tmp_path / "Descargas reales"
    downloads.mkdir()
    target = downloads / "Prueba.txt"
    target.write_text("keep until confirmed", encoding="utf-8")
    context = Context(cwd=str(tmp_path), known_directories={"Downloads": str(downloads)})
    plan, assessment = asyncio.run(Engine(Config(ai={"command_only": False})).plan(phrase, context))
    assert plan.intent == "execute" and plan.actions[0].path == str(target)
    assert plan.trace.source == "local" and assessment.level == Risk.CONFIRM
    assert target.read_text(encoding="utf-8") == "keep until confirmed"


def test_hidden_extension_ambiguity_never_selects_a_file(tmp_path: Path) -> None:
    for name in ("Prueba.txt", "Prueba.csv"):
        (tmp_path / name).touch()
    plan = local_plan("borra Prueba", Context(cwd=str(tmp_path)))
    assert plan and plan.intent == "clarify" and len(plan.choices) == 2
    assert not plan.actions


@pytest.mark.parametrize("name", ["notas de trabajo.txt", "informe en curso.txt", "archivo llamado informe.txt"])
def test_literal_paths_are_not_reinterpreted_as_prose(tmp_path: Path, name: str) -> None:
    target = tmp_path / name
    target.touch()
    for value in (str(target), name):
        resolved, ambiguous = resolve_reference(value, Context(cwd=str(tmp_path)))
        assert resolved == target and not ambiguous
    assert target.exists()


def test_model_reads_actual_file_before_answering(tmp_path: Path) -> None:
    target = tmp_path / "registro.txt"
    target.write_text("Contador real: 713\ntoken=TOPSECRET", encoding="utf-8")
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen3"}})
        data = json.loads(request.content)
        calls.append(data)
        context = json.loads(data["messages"][1]["content"])["context"]
        if len(calls) == 1:
            plan = Plan(
                intent="inspect",
                shell="cmd",
                summary="Leer registro",
                actions=[Action(kind="read", path="registro.txt")],
            )
        else:
            assert "inspect" not in data["format"]["properties"]["intent"]["enum"]
            assert "actions" not in data["format"]["properties"]
            assert "713" in context["evidence"][0]["content"]
            assert "TOPSECRET" not in context["evidence"][0]["content"]
            plan = Plan(intent="explain", shell="cmd", summary="El contador observado es 713.")
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b-instruct",
                "eval_count": 25,
                "message": {"content": plan.model_dump_json()},
            },
        )

    provider = OllamaProvider(Config(ai={"command_only": False}).ai, httpx.MockTransport(handle))
    plan, _ = asyncio.run(
        Engine(Config(ai={"command_only": False}), provider).plan("qué contiene registro.txt", Context(cwd=str(tmp_path)))
    )
    assert plan.trace.calls == 2 and plan.trace.inspections == 1 and plan.trace.output_tokens == 50
    assert "713" in plan.summary and plan.trace.source == "qwen"
    assert target.exists()


@pytest.mark.parametrize("path", ["Downloads/Prueba.txt", r"Descargas\Prueba", "Downloads/Prueba"])
def test_directory_alias_prefix_and_hidden_extension(tmp_path: Path, path: str) -> None:
    downloads = tmp_path / "redirected downloads"
    downloads.mkdir()
    target = downloads / "Prueba.txt"
    target.touch()
    plan, risk = asyncio.run(Engine(Config(ai={"command_only": False})).plan("borra " + path, Context(cwd=str(tmp_path), known_directories={"Downloads": str(downloads)})))
    assert plan.actions[0].path == str(target) and risk.level == Risk.CONFIRM
    assert target.exists()


def test_fabricated_state_answer_is_not_presented(tmp_path: Path) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen3"}})
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": Plan(
                        intent="explain", shell="cmd", summary="Tu archivo contiene 99 líneas."
                    ).model_dump_json()
                }
            },
        )

    provider = OllamaProvider(Config(ai={"command_only": False}).ai, httpx.MockTransport(handle))
    with pytest.raises(ProviderError, match="without checking"):
        asyncio.run(
            Engine(Config(ai={"command_only": False}), provider).plan("qué contiene registro.txt", Context(cwd=str(tmp_path)))
        )


def test_inspection_cannot_write_or_escape_scope(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Plan(
            intent="inspect",
            shell="cmd",
            summary="write",
            actions=[Action(kind="create", path="oops.txt")],
        )
    result = inspect_action(
        Action(kind="read", path=str(tmp_path.parent / "outside.txt")), Context(cwd=str(tmp_path))
    )
    assert not result["ok"] and "limited" in result["error"]
    assert not (tmp_path / "oops.txt").exists()


def test_incomplete_file_samples_are_explicit(tmp_path: Path) -> None:
    for i in range(50):
        (tmp_path / f"entry-{i}.txt").touch()
    result = inspect_action(Action(kind="list", path=str(tmp_path)), Context(cwd=str(tmp_path)))
    assert result["ok"] and not result["complete"] and result["matched_count"] == 40


def test_inspection_reads_hidden_extension_and_windows_utf16(tmp_path: Path) -> None:
    (tmp_path / "Prueba.txt").write_text("Contador: 713 · niño", encoding="utf-16")
    result = inspect_action(Action(kind="read", path="Prueba"), Context(cwd=str(tmp_path)))
    assert result["ok"] and result["content"] == "Contador: 713 · niño"
    assert result["encoding"] == "utf-16"


def test_forced_model_bypasses_local_rule(tmp_path: Path) -> None:
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"general.architecture": "qwen3"}})
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b-instruct",
                "eval_count": 20,
                "message": {
                    "content": Plan(
                        intent="execute",
                        shell="cmd",
                        summary="Listar",
                        actions=[Action(kind="list", path=str(tmp_path))],
                    ).model_dump_json()
                },
            },
        )

    config = Config(ai={"command_only": False})
    config.ai.prefer_model = True
    plan, _ = asyncio.run(
        Engine(config, OllamaProvider(config.ai, httpx.MockTransport(handle))).plan(
            "lista los archivos", Context(cwd=str(tmp_path))
        )
    )
    assert len(calls) == 1 and plan.trace.source == "qwen"


def test_explicit_summary_reads_target_before_single_model_call(tmp_path: Path) -> None:
    (tmp_path / "registro.txt").write_text("Contador real 713.", encoding="utf-8")
    calls=[]
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200,json={"model_info":{"general.architecture":"qwen3"}})
        body=json.loads(request.content)
        calls.append(body)
        evidence=json.loads(body["messages"][1]["content"])["context"]["evidence"]
        assert evidence[0]["ok"] and "713" in evidence[0]["content"]
        assert "actions" not in body["format"]["properties"]
        return httpx.Response(200,json={"message":{"content":'{"intent":"explain","summary":"El contador es 713."}'},"eval_count":15})
    cfg=Config(ai={"command_only": False})
    plan,_=asyncio.run(Engine(cfg,OllamaProvider(cfg.ai,httpx.MockTransport(handle))).plan("Resume registro.txt",Context(cwd=str(tmp_path))))
    assert len(calls)==1 and plan.trace.inspections==1 and "713" in plan.summary


def test_forced_creation_schema_has_no_shell_command_variant(tmp_path: Path) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200,json={"model_info":{"general.architecture":"qwen3"}})
        body=json.loads(request.content)
        assert body["format"]["$defs"]["Action"]["properties"]["kind"]["const"]=="create"
        return httpx.Response(200,json={"message":{"content":Plan(intent="execute",shell="cmd",summary="Ya creado",actions=[Action(kind="create",path="saludo.txt",content="Hola")]).model_dump_json()}})
    cfg=Config(ai={"command_only": False})
    cfg.ai.prefer_model=True
    plan,risk=asyncio.run(Engine(cfg,OllamaProvider(cfg.ai,httpx.MockTransport(handle))).plan('crea un archivo llamado saludo.txt con contenido "Hola"',Context(cwd=str(tmp_path))))
    assert risk.level==Risk.CONFIRM and "awaiting" in plan.summary
    assert not (tmp_path/'saludo.txt').exists()


def test_unrecognized_query_wording_closes_inspection_round(tmp_path: Path) -> None:
    (tmp_path/'registro.txt').write_text('El contador real es 713.',encoding='utf-8')
    calls=[]
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path=='/api/show':
            return httpx.Response(200,json={'model_info':{'general.architecture':'qwen3'}})
        body=json.loads(request.content)
        calls.append(body)
        if len(calls)==1:
            content=Plan(intent='inspect',shell='cmd',summary='Leer datos',actions=[Action(kind='read',path='registro.txt')]).model_dump_json()
        else:
            assert 'actions' not in body['format']['properties']
            evidence=json.loads(body['messages'][1]['content'])['context']['evidence']
            assert evidence[0]['ok'] and '713' in evidence[0]['content']
            content='{"intent":"explain","summary":"El contador observado es 713."}'
        return httpx.Response(200,json={'message':{'content':content},'eval_count':15})
    cfg=Config(ai={"command_only": False})
    plan,_=asyncio.run(Engine(cfg,OllamaProvider(cfg.ai,httpx.MockTransport(handle))).plan('Describe registro.txt',Context(cwd=str(tmp_path))))
    assert len(calls)==2 and plan.trace.inspections==1 and '713' in plan.summary
