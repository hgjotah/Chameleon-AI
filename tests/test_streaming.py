import asyncio
import json

import httpx
import pytest

from chameleon.core.config import Config
from chameleon.core.context import Context
from chameleon.llm.base import ProviderError
from chameleon.llm.ollama import OllamaProvider


def transport(events: list[dict]) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/api/show':
            return httpx.Response(200,json={'model_info': {'general.architecture':'qwen3'}})
        body=json.loads(request.content)
        assert body['stream'] and body['options']['num_thread']<=4
        assert 'Required JSON schema' not in body['messages'][0]['content']
        return httpx.Response(200,headers={'content-type':'application/x-ndjson'},content='\n'.join(json.dumps(e) for e in events))
    return httpx.MockTransport(handle)


def test_streamed_plan_is_complete_and_progress_is_observed() -> None:
    progress=[]
    events=[{'message':{'content':'{"intent":"explain","shell":"cmd",'}},
            {'message':{'content':'"summary":"Respuesta."}'},'done':True,'model':'qwen3:4b-instruct','eval_count':15}]
    provider=OllamaProvider(Config().ai,transport(events),progress.append)
    plan=asyncio.run(provider.plan('explica una variable',Context(cwd='C:/')))
    assert plan.summary=='Respuesta.' and plan.trace.output_tokens==15
    assert progress and progress[0].startswith('QWEN GENERANDO')


@pytest.mark.parametrize('ending',[{}, {'done':True,'done_reason':'length'}, {'error':'runner failed'}])
def test_incomplete_or_failed_stream_is_never_a_plan(ending: dict) -> None:
    events=[{'message':{'content':'{"intent":"execute","shell":"cmd","summary":"Crear", "actions":[{"kind":"create","path":"a.txt","content":""}]}'}}]
    events.append(ending)
    with pytest.raises(ProviderError):
        asyncio.run(OllamaProvider(Config().ai,transport(events)).plan('crear',Context(cwd='C:/')))


def test_installed_backend_is_started_on_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from chameleon.setup import ollama_install
    started=[]
    async def start(progress: object) -> None:
        started.append(True)
    monkeypatch.setattr(ollama_install,'ensure_server',start)
    attempts=0
    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts+=1
        if attempts==1:
            raise httpx.ConnectError('offline',request=request)
        return httpx.Response(200,json={'model_info':{'general.architecture':'qwen3'}})
    async def run() -> None:
        provider=OllamaProvider(Config().ai,httpx.MockTransport(handle))
        async with provider.client() as client:
            await provider.local_metadata(client)
    asyncio.run(run())
    assert started==[True] and attempts==2


@pytest.mark.parametrize('phrase,kind',[('busca archivos python mayores de 1 MB','find'),('muestra procesos que usan memoria','processes')])
def test_direct_query_does_not_enter_inspection_loop(phrase: str, kind: str) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/api/show':
            return httpx.Response(200,json={'model_info': {'general.architecture':'qwen3'}})
        body=json.loads(request.content)
        assert 'inspect' not in body['format']['properties']['intent']['enum']
        assert body['format']['$defs']['Action']['properties']['kind']['const']==kind
        action={'kind':kind,'path':'C:/'} if kind=='find' else {'kind':kind}
        return httpx.Response(200,json={'message':{'content':json.dumps({'intent':'execute','shell':'cmd','summary':'Mostrar resultados','actions':[action]})}})
    plan=asyncio.run(OllamaProvider(Config().ai,httpx.MockTransport(handle)).plan(phrase,Context(cwd='C:/')))
    assert plan.intent=='execute' and plan.actions[0].kind==kind
