import asyncio
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

import httpx

from chameleon.platform.windows.shells import ps_quote
from chameleon.platform.windows.system import hidden_run, launch, shell_executable


def ollama_executable() -> str | None:
    found = shutil.which("ollama")
    candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return found or (str(candidate) if candidate.is_file() else None)


async def ensure_server(progress: Callable[[str], None]) -> None:
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            response = await client.get("http://127.0.0.1:11434/api/version", timeout=2)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
    executable = ollama_executable()
    if not executable:
        raise OSError(
            "Ollama no está instalado. Instálalo desde https://ollama.com/download/windows"
        )
    progress("Iniciando Ollama local")
    environment = dict(os.environ, OLLAMA_NO_CLOUD="1", OLLAMA_HOST="127.0.0.1:11434")
    launch(
        [executable, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=0x08000000,
        env=environment,
    )
    async with httpx.AsyncClient(trust_env=False) as client:
        for _ in range(30):
            try:
                response = await client.get("http://127.0.0.1:11434/api/version", timeout=2)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                await asyncio.sleep(1)
    raise OSError("Ollama no respondió. Consulta chameleon doctor.")


def install_ollama(progress: Callable[[str], None]) -> None:
    # Called only after explicit GUI consent. TLS + Authenticode; no untrusted mirror.
    with tempfile.TemporaryDirectory(prefix="chameleon-ollama-") as directory:
        installer = Path(directory) / "OllamaSetup.exe"
        progress("Descargando Ollama desde su fuente oficial")
        with httpx.Client(timeout=60, follow_redirects=True, trust_env=False) as client:
            with client.stream("GET", "https://ollama.com/download/OllamaSetup.exe") as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                completed = 0
                with installer.open("wb") as stream:
                    for chunk in response.iter_bytes():
                        stream.write(chunk)
                        completed += len(chunk)
                        if total:
                            progress(f"Descargando Ollama: {completed * 100 // total}%")
        script = f"$s=Get-AuthenticodeSignature -LiteralPath {ps_quote(str(installer))}; if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Ollama'){{exit 1}}"
        result = hidden_run(
            [shell_executable("powershell"), "-NoProfile", "-Command", script], timeout=30
        )
        if result.returncode:
            raise OSError("Firma Authenticode de Ollama inválida. No se ejecutó el instalador.")
        progress("Instalando Ollama (firma verificada)")
        completed_process = hidden_run(
            [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
            timeout=900,
        )
        if completed_process.returncode:
            raise OSError("El instalador oficial de Ollama falló. Usa la instalación manual.")
