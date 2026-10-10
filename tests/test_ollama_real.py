import asyncio
import os

import httpx
import pytest

from chameleon.core.config import Config
from chameleon.core.context import Context
from chameleon.llm.ollama import OllamaProvider


class LoopbackOnlyTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        assert request.url.host == "127.0.0.1", "External network access during inference"
        return await super().handle_async_request(request)


@pytest.mark.ollama
@pytest.mark.parametrize(
    "prompt,kind",
    [
        ("muestra los procesos que usan más memoria", "processes"),
        ("busca todos los archivos python mayores de 1 MB", "find"),
        ("find PDF files modified since 2026-10-05", "find"),
        ("Explain briefly what Chameleon does; intent explain", None),
    ],
)
def test_real_structured_output(context: Context, prompt: str, kind: str | None) -> None:
    if os.environ.get("CHAMELEON_TEST_OLLAMA") != "1":
        pytest.skip("Set CHAMELEON_TEST_OLLAMA=1 to run actual local inference")
    # No external network route is accepted by this inference transport.
    provider = OllamaProvider(Config().ai, LoopbackOnlyTransport())
    online, present = asyncio.run(provider.status())
    assert online and present
    plan = asyncio.run(provider.plan(prompt, context))
    assert plan.shell == "cmd" and plan.version == 1
    if kind:
        assert plan.intent == "execute" and plan.actions[0].kind == kind
        if "1 MB" in prompt:
            assert plan.actions[0].min_size_bytes >= 1000000
            assert plan.actions[0].pattern == "*.py"
        if "2026-10-05" in prompt:
            assert plan.actions[0].modified_after is not None
    else:
        assert plan.intent == "explain" and not plan.actions
