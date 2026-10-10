import os
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Literal

import tomli_w
from pydantic import BaseModel, ConfigDict, Field, field_validator

from chameleon.core.schemas import ShellName


def data_dir() -> Path:
    override = os.environ.get("CHAMELEON_HOME")
    return (
        Path(override)
        if override
        else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ChameleonAI"
    )


def asset_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets"


class StrictSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class AIConfig(StrictSettings):
    provider: Literal["ollama"] = "ollama"
    model: str = "qwen3:4b-instruct"
    enabled: bool = True
    timeout: int = Field(default=90, ge=5, le=600)
    keep_alive: str = "5m"
    show_generated_commands: bool = False

    @field_validator("model")
    @classmethod
    def local_model_only(cls, value: str) -> str:
        if not value.strip() or ":cloud" in value.casefold() or value.casefold().endswith("-cloud"):
            raise ValueError("Solo se admiten modelos locales descargados; cloud no está permitido")
        return value


class TerminalConfig(StrictSettings):
    shell: ShellName = "cmd"
    start_directory: str = ""
    font: str = "Cascadia Mono, Consolas, monospace"
    font_size: int = Field(default=14, ge=8, le=40)
    cursor_style: Literal["block", "bar", "underline"] = "block"
    cursor_blink: bool = True
    scrollback: int = Field(default=10000, ge=100, le=100000)


class PrivacyConfig(StrictSettings):
    save_ai_history: bool = False


class SafetyConfig(StrictSettings):
    strict_mode: bool = False


class GeneralConfig(StrictSettings):
    language: Literal["es", "en"] = "es"
    startup_checks: bool = True


class Config(StrictSettings):
    ai: AIConfig = Field(default_factory=AIConfig)
    terminal: TerminalConfig = Field(default_factory=TerminalConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    general: GeneralConfig = Field(default_factory=GeneralConfig)


def save_config(config: Config, root: Path | None = None) -> None:
    path = (root or data_dir()) / "config" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix="config-", suffix=".tmp", delete=False
    ) as stream:
        stream.write(tomli_w.dumps(config.model_dump()))
        temp = Path(stream.name)
    temp.replace(path)


def load_config(root: Path | None = None) -> tuple[Config, str | None]:
    path = (root or data_dir()) / "config" / "config.toml"
    if not path.exists():
        return Config(), None
    try:
        return Config.model_validate(tomllib.loads(path.read_text(encoding="utf-8"))), None
    except (ValueError, OSError) as exc:
        backup = path.with_suffix(f".broken-{time.time_ns()}.toml")
        path.replace(backup)
        config = Config()
        save_config(config, root)
        return (
            config,
            f"Configuración dañada; defaults restaurados. Backup: {backup.name} ({type(exc).__name__})",
        )
