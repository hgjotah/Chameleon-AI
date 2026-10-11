"""Installer orchestration independent of widgets and the Qt event loop."""

import asyncio
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from chameleon.core.config import load_config
from chameleon.llm.base import ProviderError
from chameleon.llm.ollama import OllamaProvider
from chameleon.platform.windows.installer import (
    install,
    profile_paths,
    read_manifest,
    write_manifest,
)
from chameleon.platform.windows.system import hidden_run, shell_executable
from chameleon.setup.ollama_install import ensure_server, install_ollama, ollama_executable


@dataclass(frozen=True)
class InstallOptions:
    allow_ollama: bool = False
    pull_model: bool = True
    allow_policy: bool = False
    desktop: bool = False


class SetupService:
    def __init__(self, root: Path, payload: Path, progress: Callable[[str], None]) -> None:
        self.root = root
        self.payload = payload
        self.progress = progress

    def run(self, options: InstallOptions) -> str:
        if os.name != "nt" or sys.getwindowsversion().build < 17763:
            raise OSError("Se requiere Windows 10 1809+ / Windows 11 x64")
        self.progress("✓ Windows compatibility · runtime incluido")
        install(self.root, self.payload, desktop=options.desktop, progress=self.progress)
        self.progress("✓ CMD · PowerShell · PATH · shortcuts · Terminal")
        manifest = read_manifest(self.root)
        try:
            self.configure_policies(options.allow_policy, manifest)
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.progress("⚠ Terminal instalado; no se pudieron verificar las políticas de PowerShell: " + str(exc))
        try:
            ai_ready = self.configure_ai(options, manifest)
        except (ProviderError, OSError, TimeoutError, subprocess.TimeoutExpired, httpx.HTTPError) as exc:
            self.progress("⚠ Terminal instalado. IA pendiente: " + str(exc))
            return "Terminal instalado correctamente. La IA necesita atención; consulta el detalle y pulsa Reparar para reintentar. Las acciones locales ya funcionan."
        if not ai_ready:
            return "Terminal instalado correctamente. La IA necesita atención: Ollama o el modelo no están disponibles. Pulsa Reparar cuando estén listos. Las acciones locales ya funcionan."
        return "Instalación lista. Abre una nueva terminal para aplicar PATH y perfiles."

    def configure_policies(self, allowed: bool, manifest: dict[str, Any]) -> None:
        for shell, _ in profile_paths():
            executable = shell_executable(shell)
            result = hidden_run(
                [executable, "-NoProfile", "-Command", "Get-ExecutionPolicy"], timeout=15
            )
            if result.returncode or not result.stdout.strip():
                self.progress(f"⚠ {shell}: no se pudo consultar la política. El terminal está instalado; comprueba el diagnóstico.")
                continue
            effective = result.stdout.strip()
            if effective not in ("Restricted", "AllSigned"):
                continue
            if not allowed:
                self.progress(
                    f"⚠ {shell}: {effective} impide perfiles. No se cambió la política. Consulta INSTALLATION.md."
                )
                continue
            before = hidden_run(
                [executable, "-NoProfile", "-Command", "Get-ExecutionPolicy -Scope CurrentUser"],
                timeout=15,
            ).stdout.strip()
            changed = hidden_run(
                [
                    executable,
                    "-NoProfile",
                    "-Command",
                    "Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force; Get-ExecutionPolicy",
                ],
                timeout=15,
            )
            if changed.returncode or changed.stdout.strip() != "RemoteSigned":
                self.progress("⚠ Group Policy impide la integración. Consulta INSTALLATION.md.")
            else:
                manifest.setdefault("policy_before", {}).setdefault(shell, before)
                write_manifest(self.root, manifest)

    def configure_ai(self, options: InstallOptions, manifest: dict[str, Any]) -> bool:
        config, _ = load_config(self.root)
        provider = OllamaProvider(config.ai)
        self.progress("Comprobando Ollama instalado y modelo " + config.ai.model)
        online, present = asyncio.run(provider.status())
        if not online:
            if not ollama_executable() and options.allow_ollama:
                install_ollama(self.progress)
                if not ollama_executable():
                    raise OSError("El instalador terminó pero no se encuentra ollama.exe. No se declara la IA instalada.")
                manifest["installed_ollama"] = True
                write_manifest(self.root, manifest)
            if ollama_executable():
                asyncio.run(ensure_server(self.progress))
            else:
                self.progress(
                    "IA pendiente: instala Ollama desde https://ollama.com/download/windows; luego Repair."
                )
        online, present = asyncio.run(provider.status())
        if online and not present and options.pull_model:
            self.progress("Descargando " + config.ai.model + " (~2,5 GB); espera a la verificación final")
            asyncio.run(provider.pull(self.progress))
            manifest["downloaded_model"] = config.ai.model
            write_manifest(self.root, manifest)
            present = True
        if online and present:
            self.progress("✓ Modelo local encontrado: " + config.ai.model)
            self.progress("Verificando inferencia estructurada local")
            asyncio.run(provider.probe())
            self.progress("✓ Ollama · Qwen · Local inference")
            return True
        else:
            self.progress("⚠ AI OFFLINE. Las reglas locales y el terminal funcionan.")
            return False
