import json
import re
from collections.abc import Callable

import httpx
from pydantic import ValidationError

from chameleon.core.config import AIConfig
from chameleon.core.context import Context
from chameleon.core.privacy import redact
from chameleon.core.schemas import Plan, generation_schema
from chameleon.llm.base import LLMProvider, ProviderError
from chameleon.llm.prompts import SYSTEM_PROMPT

LOCAL_API = "http://127.0.0.1:11434"


class OllamaProvider(LLMProvider):
    def __init__(self, config: AIConfig, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.config = config
        self.transport = transport

    def client(self) -> httpx.AsyncClient:
        # No proxies, redirects, remote endpoints or cloud fallback.
        return httpx.AsyncClient(
            base_url=LOCAL_API,
            timeout=self.config.timeout,
            trust_env=False,
            transport=self.transport,
        )

    async def plan(self, request: str, context: Context) -> Plan:
        schema = generation_schema()
        schema["properties"]["shell"] = {"type": "string", "const": context.shell}
        # Route unmistakable file-query requests to a smaller action grammar. The
        # model still interprets the paths, patterns, sizes and dates; it cannot
        # silently replace a file query with an unrelated process operation.
        if re.match(r"\s*(?:busca|encuentra|find|search|locate)\b", request, re.I) and re.search(
            r"\b(?:archivos?|files?|pdf|pdfs)\b", request, re.I
        ):
            variants = schema["$defs"]["Action"]["anyOf"]
            schema["$defs"]["Action"] = next(
                variant for variant in variants if variant["properties"]["kind"]["const"] == "find"
            )
        elif re.match(r"\s*(?:muestra|muestrame|muéstrame|lista|show|list|dime)\b", request, re.I) and re.search(r"\b(?:procesos|processes)\b", request, re.I):
            schema["$defs"]["Action"] = next(variant for variant in schema["$defs"]["Action"]["anyOf"] if variant["properties"]["kind"]["const"] == "processes")
        elif re.match(r"\s*(?:explain|explica|what is|qu[eé] es)\b", request, re.I):
            schema["properties"]["intent"] = {"const": "explain", "type": "string"}
            schema["properties"]["actions"] = {"type": "array", "items": {}, "maxItems": 0}
            schema.pop("$defs", None)
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT + "\nRequired JSON schema:\n" + json.dumps(schema, separators=(",", ":")),
            },
            {
                "role": "user",
                "content": redact(
                    json.dumps(
                        {"request": request[:8000], "context": context.model_payload(request)},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                ),
            },
        ]
        async with self.client() as client:
            for attempt in range(2):
                if attempt == 0:
                    try:
                        metadata_response = await client.post(
                            "/api/show", json={"model": self.config.model}, timeout=5
                        )
                        metadata_response.raise_for_status()
                        metadata = metadata_response.json()
                        if (
                            metadata.get("remote_host")
                            or metadata.get("remote_model")
                            or not metadata.get("model_info")
                        ):
                            raise ProviderError(
                                "El modelo no es una descarga local verificable. No se envió la petición."
                            )
                    except httpx.HTTPError as exc:
                        raise ProviderError(
                            'Modelo local no disponible. Ejecuta "chameleon doctor".'
                        ) from exc
                content = ""
                try:
                    response = await client.post(
                        "/api/chat",
                        json={
                            "model": self.config.model,
                            "messages": messages,
                            "stream": False,
                            "format": schema,
                            "think": False,
                            "keep_alive": self.config.keep_alive,
                            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 768},
                        },
                    )
                    response.raise_for_status()
                    content = response.json()["message"]["content"]
                    plan = Plan.model_validate_json(content)
                    if plan.shell != context.shell:
                        raise ValueError("Wrong target shell")
                    return plan
                except (ValidationError, ValueError, KeyError) as exc:
                    if attempt == 0:
                        if content:
                            messages.append({"role": "assistant", "content": content[:16000]})
                        errors = (
                            str(exc.errors(include_input=False, include_url=False))
                            if isinstance(exc, ValidationError)
                            else "Invalid JSON envelope or incorrect target shell"
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": "Correct the previous JSON. Validation errors: "
                                + errors[:2000]
                                + ". An execute intent MUST contain at least one typed action. "
                                "Other intents MUST have actions: []. Match the target shell.",
                            }
                        )
                except httpx.TimeoutException as exc:
                    raise ProviderError("El modelo local tardó demasiado. Prueba una petición más concreta o aumenta el tiempo límite en Ajustes → IA. Ctrl+C cancela; los comandos y las acciones locales siguen disponibles.") from exc
                except httpx.HTTPError as exc:
                    raise ProviderError(
                        'IA local no disponible. Ejecuta "chameleon doctor".'
                    ) from exc
        raise ProviderError("El modelo devolvió una acción inválida dos veces. No se ejecutó nada.")

    async def status(self) -> tuple[bool, bool]:
        try:
            async with self.client() as client:
                response = await client.get("/api/tags", timeout=3)
                response.raise_for_status()
                names = {
                    m["name"]
                    for m in response.json().get("models", [])
                    if not m.get("remote_host") and not m.get("remote_model")
                }
                return True, self.config.model in names
        except (httpx.HTTPError, ValueError, KeyError):
            return False, False

    async def pull(self, progress: Callable[[str], None]) -> None:
        async with self.client() as client:
            try:
                async with client.stream(
                    "POST",
                    "/api/pull",
                    json={"model": self.config.model},
                    timeout=httpx.Timeout(30, read=600),
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        event = json.loads(line)
                        if "error" in event:
                            raise ProviderError(event["error"])
                        total = event.get("total", 0)
                        percent = f" {event.get('completed', 0) * 100 // total}%" if total else ""
                        progress(event.get("status", "") + percent)
            except httpx.HTTPError as exc:
                raise ProviderError("No se pudo descargar el modelo desde Ollama.") from exc
        online, present = await self.status()
        if not (online and present):
            raise ProviderError("La descarga no se pudo verificar.")

    async def probe(self) -> None:
        # Verify local metadata before sending a minimal structured generation.
        # A complete action plan needlessly generated hundreds of tokens here.
        async with self.client() as client:
            try:
                metadata = await client.post("/api/show", json={"model": self.config.model}, timeout=5)
                metadata.raise_for_status()
                info = metadata.json()
                if info.get("remote_host") or info.get("remote_model") or not info.get("model_info"):
                    raise ProviderError("El modelo no es una descarga local verificable.")
                result = await client.post("/api/chat", json={
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": 'Return exactly {"ok":true}.'}],
                    "format": {"type": "object", "properties": {"ok": {"const": True}}, "required": ["ok"], "additionalProperties": False},
                    "stream": False, "think": False, "keep_alive": self.config.keep_alive,
                    "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 16},
                })
                result.raise_for_status()
                if json.loads(result.json()["message"]["content"]) != {"ok": True}:
                    raise ProviderError("La prueba de inferencia local no devolvió el resultado esperado.")
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                raise ProviderError("No se completó la prueba del modelo local. El terminal está instalado; usa Reparar para reintentar la IA.") from exc
