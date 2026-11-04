"""Local Ollama model discovery and persistent CLI selection."""

import re
from collections.abc import Callable
from pathlib import Path

import httpx

from chameleon.cli_ui import Choice, select
from chameleon.core.config import Config, load_config, save_config
from chameleon.llm.base import ProviderError
from chameleon.llm.models import MODELS, model_description
from chameleon.llm.ollama import LOCAL_API, OllamaProvider


async def installed_models(transport: httpx.AsyncBaseTransport | None = None) -> list[str]:
    try:
        async with httpx.AsyncClient(
            base_url=LOCAL_API, timeout=5, trust_env=False, transport=transport
        ) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Invalid Ollama response")
            models = payload["models"]
            if not isinstance(models, list):
                raise ValueError("Invalid model list")
            tags = set()
            for model in models:
                if not isinstance(model, dict):
                    continue
                tag = model.get("name")
                if (
                    isinstance(tag, str)
                    and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/:-]{0,254}", tag)
                    and ":cloud" not in tag.casefold()
                    and not tag.casefold().endswith("-cloud")
                    and not model.get("remote_host")
                    and not model.get("remote_model")
                ):
                    tags.add(tag)
            return sorted(tags, key=lambda tag: (tag not in MODELS, tag.casefold()))
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise ProviderError(
            "Could not retrieve the local Ollama model list (127.0.0.1:11434). Open Ollama or prepare AI in Setup and try again. The model was not changed."
        ) from exc


async def change_model(root: Path, config: Config, tag: str, output: Callable[[str], None]) -> int:
    tags = await installed_models()
    if not tags:
        output("No local models are downloaded. Prepare them in Setup or Settings → Local AI.")
        return 1
    if not tag:
        selected = select(
            "CHAMELEON · CHANGE MODEL",
            [Choice(name, "CURRENT" if name == config.ai.model else model_description(name)) for name in tags],
            tags.index(config.ai.model) if config.ai.model in tags else 0,
            "Models downloaded in Ollama. Your selection is saved for future requests.",
        )
        if selected is None:
            output("Cancelled. The model has not changed.")
            return 1
        tag = tags[selected]
    if tag not in tags:
        output(f"The model {tag!r} is not downloaded. Run chameleon ai --models.")
        return 1
    candidate = config.ai.model_copy(deep=True)
    candidate.model = tag
    provider = OllamaProvider(candidate)
    try:
        async with provider.client() as client:
            await provider.local_metadata(client)
    except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
        raise ProviderError("Could not verify the local model. The selection was not changed.") from exc
    # Reload after interaction/network IO: preserve settings changed meanwhile.
    current, warning = load_config(root)
    if warning:
        output(warning)
        return 1
    current.ai.model = tag
    save_config(current, root)
    output(f"Selected model: {tag}")
    output("Saved for future CLI requests and new terminal windows.")
    return 0
