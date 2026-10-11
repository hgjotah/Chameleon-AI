import argparse
import asyncio
import base64
import json
import logging
import os
import sys
from io import TextIOWrapper
from pathlib import Path

from chameleon import __version__
from chameleon.core.config import data_dir, load_config
from chameleon.core.context import build_context
from chameleon.core.engine import Engine
from chameleon.core.intents import refine_request
from chameleon.core.privacy import configure_logging, redact
from chameleon.core.schemas import Action, ShellName
from chameleon.core.sessions import SessionStore
from chameleon.llm.base import ProviderError
from chameleon.platform.windows.protocol import emit_cmd
from chameleon.platform.windows.shells import CmdAdapter, PowerShellAdapter, describe_action
from chameleon.safety.engine import Risk


def human(message: str) -> None:
    print(message, file=sys.stderr)


def ask(message: str) -> str:
    human(message)
    # Redirected shells can still use their attached console. Headless runs decline.
    try:
        if os.environ.get("CHAMELEON_NONINTERACTIVE"):
            return ""
        if sys.stdin.isatty():
            return input()
        if os.name == "nt" and not os.environ.get("CHAMELEON_NONINTERACTIVE"):
            with open("CONIN$", encoding="utf-8") as console:
                return console.readline().strip()
    except (OSError, EOFError):
        return ""
    return ""


async def run(args: argparse.Namespace) -> int:
    root = data_dir()
    config, warning = load_config(root)
    configure_logging(root, args.debug)
    if warning:
        human(warning)
    operation = args.operation or "help"
    if operation == "apply":
        from chameleon.core.files import apply_file_action
        from chameleon.safety.engine import RiskEngine

        action = Action.model_validate_json(base64.b64decode(args.encoded or "", validate=True))
        from chameleon.platform.windows.system import WindowsPlatform

        decision = RiskEngine(WindowsPlatform().system_directory()).action(action, Path.cwd())
        if decision.level == Risk.BLOCKED:
            raise ValueError(decision.reason)
        print(apply_file_action(action))
        return 0
    if operation == "query":
        from chameleon.core.queries import file_query, process_query

        action = Action.model_validate_json(base64.b64decode(args.encoded or "", validate=True))
        if action.kind == "processes":
            print(f"{'Process':30} {'PID':>8} {'RAM MB':>12}")
            for name, pid, memory in process_query(action.limit):
                print(f"{name:30} {pid:8} {memory / 1048576:12.1f}")
        elif action.kind in ("find", "list"):
            for path in file_query(action, Path(args.cwd or os.getcwd())):
                print(path)
        else:
            raise ValueError("Operación de consulta inválida")
        return 0
    if operation in ("help", "version"):
        human(
            f"Chameleon AI {__version__}"
            + (
                "\nUso: chameleon ai [--show] [--dry-run] [--model] <petición>\n     chameleon status | doctor | version | terminal | settings | setup"
                if operation == "help"
                else ""
            )
        )
        return 0
    if operation in ("terminal", "settings", "setup"):
        if operation == "setup" and args.install:
            from chameleon.platform.windows.installer import read_manifest
            from chameleon.setup.service import InstallOptions, SetupService
            payload = Path(args.payload) if args.payload else Path(sys.executable).parent
            if not getattr(sys, "frozen", False):
                raise ValueError("Para instalar utiliza el ejecutable independiente ChameleonCore.exe setup --install --payload <carpeta>, o ChameleonSetup.exe.")
            message = await asyncio.to_thread(
                SetupService(root, payload, human).run,
                InstallOptions(allow_ollama=args.install_ollama, pull_model=args.download_model or args.install_ollama, desktop=read_manifest(root).get("desktop_shortcut", False)),
            )
            human(message)
            return 3 if "necesita atención" in message else 0
        if operation == "terminal":
            from chameleon.terminal.app import main as gui
        else:
            from chameleon.setup.app import main as gui
        return gui([operation])
    if operation in ("status", "doctor"):
        from chameleon.setup.doctor import diagnose

        results = await diagnose(root, config)
        human("Chameleon Doctor\n")
        for item in results:
            human(f"[{'OK' if item.ok else 'FAIL'}] {item.name}: {item.detail}")
        return 0 if all(r.ok for r in results) else 1
    if operation != "ai":
        human("Operación desconocida. Ejecuta chameleon --help.")
        return 2
    request = " ".join(args.request).strip()
    if not request:
        human("Escribe una petición después de chameleon ai.")
        return 2
    shell: ShellName = "cmd" if args.emit == "cmd" else "powershell"
    shell = args.shell or shell
    store = SessionStore(root, args.session)
    cwd = Path(args.cwd or os.getcwd()).resolve()
    ctx = build_context(cwd, shell, store.recent())
    engine = Engine(config, progress=human)
    if args.model:
        config.ai.prefer_model = True
    for _ in range(4):
        plan, assessment = await engine.plan(request, ctx)
        if plan.intent != "clarify":
            break
        human(plan.summary)
        for index, choice in enumerate(plan.choices, 1):
            human(f"[{index}] {choice}")
        answer = ask("Aclara tu petición (Enter cancela):")
        if not answer:
            return 1
        if answer.isdigit() and 1 <= int(answer) <= len(plan.choices):
            answer = plan.choices[int(answer) - 1]
        request = refine_request(request, answer, plan)
        ctx.recent.append(plan.summary)
    else:
        human("Demasiadas aclaraciones. No se ejecutó nada.")
        return 1
    human("Origen: " + plan.trace.label())
    if plan.intent != "execute":
        human(plan.summary)
        return 0 if plan.intent == "explain" else 1
    adapter = CmdAdapter() if shell == "cmd" else PowerShellAdapter()
    if assessment.level == Risk.BLOCKED:
        human("Bloqueado: " + assessment.reason)
        return 1
    commands = [adapter.render(action, cwd) for action in plan.actions]
    if (
        args.show
        or args.dry_run
        or config.ai.show_generated_commands
        or assessment.level == Risk.CONFIRM
    ):
        human(plan.summary + "\n\nAcciones:\n" + "\n\n".join(describe_action(a, cwd, shell != "cmd") for a in plan.actions))
        if args.show or config.ai.show_generated_commands:
            human("\nComando generado:\n" + "\n".join(commands))
    if args.dry_run:
        return 0
    if assessment.level == Risk.CONFIRM:
        answer = ask(
            "Chameleon necesita confirmación\nRiesgo: " + assessment.reason + "\n¿Ejecutar? [y/N]"
        )
        if answer.casefold() not in ("y", "yes", "s", "si", "sí"):
            human("Cancelado.")
            return 1
    if not args.emit:
        human(
            "Para cambiar el shell actual utiliza el wrapper instalado. Ejecuta Chameleon Setup.\nPuedes revisar con --dry-run."
        )
        return 2
    store.remember(request + " → " + plan.summary)
    if config.privacy.save_ai_history:
        history = root / "history"
        history.mkdir(exist_ok=True)
        with (history / "ai.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {"request": redact(request), "summary": redact(plan.summary)},
                    ensure_ascii=False,
                )
                + "\n"
            )
    if args.emit == "cmd":
        token = emit_cmd(plan, cwd, root)
        if args.response:
            response = Path(args.response).resolve()
            expected = (root / "runtime" / "actions").resolve()
            if response.parent != expected or response.suffix != ".response":
                raise ValueError("Destino de protocolo inválido")
            with response.open("x", encoding="ascii") as stream:
                stream.write(token + "\n")
        else:
            print(token)
    else:
        print(plan.model_dump_json())
    return 0


def main(argv: list[str] | None = None) -> int:
    if isinstance(sys.stdout, TextIOWrapper) and isinstance(sys.stderr, TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Chameleon AI local", add_help=False)
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--emit", choices=("cmd", "powershell"))
    parser.add_argument("--response")
    parser.add_argument("--encoded")
    parser.add_argument("--shell", choices=("cmd", "powershell", "pwsh"))
    parser.add_argument("--session", type=int)
    parser.add_argument("--cwd")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--install-ollama", action="store_true")
    parser.add_argument("--download-model", action="store_true")
    parser.add_argument("--payload")
    parser.add_argument("operation", nargs="?")
    parser.add_argument("request", nargs="*")
    try:
        args = parser.parse_intermixed_args(argv)
        if args.help:
            args.operation = "help"
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        human("Cancelado.")
        return 130
    except (ProviderError, ValueError, OSError) as exc:
        logging.getLogger("chameleon").warning("Operation failed: %s", type(exc).__name__)
        if isinstance(exc, PermissionError):
            human(f"Windows denegó acceso a {exc.filename or 'la ruta'}. Usa una carpeta de usuario (Documentos o Escritorio) y comprueba sus permisos; no hace falta elevar la terminal para archivos normales.")
        else:
            human(str(exc))
        return 1
    except Exception:
        logging.getLogger("chameleon").exception("Internal failure")
        if "--debug" in (argv or sys.argv[1:]):
            raise
        human('Chameleon encontró un error. Ejecuta "chameleon doctor"; consulta los logs locales.')
        return 1
