"""Local model choices; arbitrary additional local Ollama tags remain supported."""

MODELS = {
    "qwen3:4b-instruct": ("Qwen 3 · 4B", "2,5 GB · mejor precisión · CPU/GPU"),
    "qwen2.5:0.5b": ("Qwen 2.5 · 0.5B", "398 MB · ligero y rápido · menor precisión"),
}


def model_description(tag: str) -> str:
    return (
        " · ".join(MODELS[tag])
        if tag in MODELS
        else "Modelo local de Ollama · tamaño según etiqueta"
    )
