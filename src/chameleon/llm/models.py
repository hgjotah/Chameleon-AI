"""Local model choices; arbitrary additional local Ollama tags remain supported."""

MODELS = {
    "qwen3:4b-instruct": ("Qwen 3 · 4B", "2.5 GB · higher accuracy · CPU/GPU"),
    "qwen2.5:0.5b": ("Qwen 2.5 · 0.5B", "398 MB · lightweight and fast · lower accuracy"),
}


def model_description(tag: str) -> str:
    return (
        " · ".join(MODELS[tag])
        if tag in MODELS
        else "Local Ollama model · size depends on the tag"
    )
