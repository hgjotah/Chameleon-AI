import os
import sys
from dataclasses import dataclass
from pathlib import Path

from chameleon.core.config import Config
from chameleon.llm.ollama import OllamaProvider
from chameleon.platform.windows.system import hidden_run, shell_executable
from chameleon.setup.ollama_install import ollama_executable


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


async def diagnose(root: Path, config: Config) -> list[Check]:
    from chameleon.platform.windows.installer import profile_paths, user_path

    checks = [
        Check(
            "Windows / ConPTY",
            os.name == "nt" and sys.getwindowsversion().build >= 17763,
            "Windows 10 1809+",
        ),
        Check("Core", True, "0.5.1"),
        Check(
            "CMD integration",
            (root / "bin" / "chameleon.cmd").is_file(),
            "PATH + wrapper; Repair si falta",
        ),
        Check(
            "PATH",
            str(root / "bin").casefold()
            in [p.casefold().rstrip("\\") for p in user_path().split(";")],
            "PATH del usuario",
        ),
    ]
    for shell, profile in profile_paths():
        content = profile.read_bytes() if profile.exists() else b""
        encoding = "utf-16" if content.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        text = content.decode(encoding, errors="replace")
        checks.append(
            Check(
                shell + " integration",
                "# >>> Chameleon AI >>>" in text and (root / "bin" / "Chameleon.psm1").exists(),
                "Profile loader; Setup → Repair",
            )
        )
        result = hidden_run(
            [shell_executable(shell), "-NoProfile", "-Command", "Get-ExecutionPolicy"], timeout=10
        )
        policy = result.stdout.strip()
        checks.append(
            Check(
                shell + " ExecutionPolicy",
                result.returncode == 0 and policy in ("RemoteSigned", "Unrestricted", "Bypass"),
                policy if result.returncode == 0 and policy else "No se pudo consultar la política. Ejecuta Setup → Reparar.",
            )
        )
    online, present = await OllamaProvider(config.ai).status()
    checks.extend(
        [
            Check("Ollama executable", bool(ollama_executable()), ollama_executable() or "Ollama no instalado; Setup → Reparar"),
            Check("Ollama Local API", online, "127.0.0.1:11434"),
            Check(config.ai.model, present, "Modelo local descargado"),
            Check("Runtime", (root / "runtime").is_dir(), "Directorio privado"),
        ]
    )
    return checks
