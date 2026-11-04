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


HELP = """Usage: chameleon ai [options] <request>

View and configure
  --version                 Show the installed version
  --model                   Show the configured model (without inference)
  --models                  List models downloaded in local Ollama
  --changemodel             Choose a model with arrows and Enter; Esc cancels
  --changemodel TAG         Select a downloaded local model without opening the list
  --help, -h                Show this help

Prepare an action
  --try <request>           Show the command and offer Run or Cancel
  --dry-run <request>       Show the proposal without offering to run it
  --show <request>          Show the command and continue with normal execution
  --force-model <request>   Force a real call to the configured model
  --debug <request>         Show the proposal source, model and diagnostics

Examples
  chameleon ai --model
  chameleon ai --changemodel
  chameleon ai --try go to Desktop
  chameleon ai --force-model --try list files

--try starts on Cancel and requires approval even with Full access.
Access policies still apply. Without an interactive console it does not execute.
For compatibility, --model followed by a request is equivalent to --force-model.

Other tools
  chameleon doctor          Diagnose installation, shells and Ollama
  chameleon status          Alias for doctor
  chameleon version         Version
  chameleon terminal        Open Chameleon Terminal
  chameleon settings        Open Settings
  chameleon setup           Open the installer / repair tool
"""


async def run(args: argparse.Namespace) -> int:
    operation = args.operation or "help"
    if operation in ("help", "version"):
        human(f"Chameleon AI {__version__}" + ("\n\n" + HELP if operation == "help" else ""))
        return 0
    root = data_dir()
    config, warning = load_config(root)
    configure_logging(root, args.debug)
    if warning:
        human(warning)
    if operation == "apply":
        from chameleon.core.files import apply_file_action
        from chameleon.safety.engine import RiskEngine

        if args.policy:
            from chameleon.core.config import SafetyConfig

            if len(args.policy) > 4096:
                raise ValueError("Execution policy is too large")
            config.safety = SafetyConfig.model_validate_json(
                base64.b64decode(args.policy, validate=True)
            )

        action = Action.model_validate_json(base64.b64decode(args.encoded or "", validate=True))
        from chameleon.platform.windows.system import WindowsPlatform

        decision = RiskEngine(WindowsPlatform().system_directory(), policy=config.safety).action(
            action, Path.cwd()
        )
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
            raise ValueError("Invalid query operation")
        return 0
    if operation in ("terminal", "settings", "setup"):
        if operation == "setup" and args.install:
            from chameleon.platform.windows.installer import read_manifest
            from chameleon.setup.service import InstallOptions, SetupService

            payload = Path(args.payload) if args.payload else Path(sys.executable).parent
            if not getattr(sys, "frozen", False):
                raise ValueError(
                    "To install, use the standalone executable ChameleonCore.exe setup --install --payload <folder>, or ChameleonSetup.exe."
                )
            message = await asyncio.to_thread(
                SetupService(root, payload, human).run,
                InstallOptions(
                    allow_ollama=args.install_ollama,
                    pull_model=args.download_model or args.install_ollama,
                    desktop=read_manifest(root).get("desktop_shortcut", False),
                ),
            )
            human(message)
            return 3 if "needs attention" in message else 0
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
        human("Unknown operation. Run chameleon --help.")
        return 2
    if args.changemodel is not None:
        from chameleon.cli_models import change_model

        return await change_model(root, config, args.changemodel, human)
    if args.models:
        from chameleon.cli_models import installed_models

        tags = await installed_models()
        human("Models downloaded in local Ollama:")
        for tag in tags:
            human(f"  {'›' if tag == config.ai.model else ' '} {tag}" + (" · current" if tag == config.ai.model else ""))
        if not tags:
            human("  None. Prepare models in Setup or Settings → Local AI.")
        return 0
    request = " ".join(args.request).strip()
    if args.model and not request and not (args.try_command or args.dry_run or args.show or args.force_model):
        human(f"Configured model: {config.ai.model}")
        human("Provider: Local Ollama · 127.0.0.1:11434")
        human("AI disabled" if not config.ai.enabled else "AI enabled")
        return 0
    if not request:
        human("Enter a request after chameleon ai.")
        return 2
    shell: ShellName = "cmd" if args.emit == "cmd" else "powershell"
    shell = args.shell or shell
    store = SessionStore(root, args.session)
    cwd = Path(args.cwd or os.getcwd()).resolve()
    ctx = build_context(cwd, shell, store.recent())
    if args.shell_version:
        ctx.shell_version = args.shell_version
    if args.shell_executable:
        ctx.shell_executable = args.shell_executable
    if args.shell_state:
        from chameleon.core.context import apply_shell_state

        apply_shell_state(ctx, args.shell_state)
    if args.model or args.force_model:
        config.ai.prefer_model = True
    engine = Engine(config, progress=human if args.debug or not config.ai.command_only else None)
    for _ in range(4):
        plan, assessment = await engine.plan(request, ctx)
        if plan.intent != "clarify":
            break
        human(plan.summary)
        for index, choice in enumerate(plan.choices, 1):
            human(f"[{index}] {choice}")
        answer = ask("Clarify your request (Enter cancels):")
        if not answer:
            return 1
        if answer.isdigit() and 1 <= int(answer) <= len(plan.choices):
            answer = plan.choices[int(answer) - 1]
        request = refine_request(request, answer, plan)
        ctx.recent.append(plan.summary)
    else:
        human("Too many clarification attempts. Nothing was executed.")
        return 1
    if args.debug or not config.ai.command_only:
        human("Source: " + plan.trace.label())
    if plan.intent != "execute":
        human(plan.summary)
        return 0 if plan.intent == "explain" else 1
    adapter = (
        CmdAdapter(plan.policy_token) if shell == "cmd" else PowerShellAdapter(plan.policy_token)
    )
    if assessment.level == Risk.BLOCKED:
        human("Blocked: " + assessment.reason)
        return 1
    commands = [adapter.render(action, cwd) for action in plan.actions]
    if args.try_command:
        from chameleon.cli_ui import Choice, select

        if not args.emit:
            human("Proposed command:\n" + "\n".join(commands))
            human("To run a proposal in the current session, use chameleon ai --try through the installed wrapper.")
            return 2
        preview = (
            f"PREVIEW · {shell.upper()}\nFolder: {cwd}\nSource: {plan.trace.label()}"
            + "\n\nCommand to run:\n\n"
            + "\n".join(commands)
            + ("\n\nPermission review: " + assessment.reason if assessment.level == Risk.CONFIRM else "")
        )
        chosen = select(
            "CHAMELEON · RUN THIS PROPOSAL?",
            [Choice("Cancel", "Do not run anything"), Choice("Run", "In the current session")],
            selected=0,
            details=preview,
        )
        if chosen != 1:
            human("Cancelled. The proposal was not executed.")
            return 1
    elif config.ai.command_only:
        human("\n".join(commands))
    if not args.try_command and (
        args.show
        or args.dry_run
        or config.ai.show_generated_commands
        or assessment.level == Risk.CONFIRM
    ):
        if not config.ai.command_only:
            human(
                plan.summary
                + "\n\nAcciones:\n"
                + "\n\n".join(describe_action(a, cwd, shell != "cmd") for a in plan.actions)
            )
        if args.show or config.ai.show_generated_commands:
            human("\nGenerated command:\n" + "\n".join(commands))
    if args.dry_run:
        return 0
    if assessment.level == Risk.CONFIRM and not args.try_command:
        answer = ask(
            "Chameleon needs confirmation\nRisk: " + assessment.reason + "\nRun? [y/N]"
        )
        if answer.casefold() not in ("y", "yes", "s", "si", "sí"):
            human("Cancelled.")
            return 1
    if not args.emit:
        human(
            "Use the installed wrapper to change the current shell. Run Chameleon Setup.\nYou can preview a proposal with --dry-run."
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
                raise ValueError("Invalid protocol destination")
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
    parser.add_argument("--policy")
    parser.add_argument("--shell", choices=("cmd", "powershell", "pwsh"))
    parser.add_argument("--shell-version")
    parser.add_argument("--shell-executable")
    parser.add_argument("--shell-state")
    parser.add_argument("--session", type=int)
    parser.add_argument("--cwd")
    parser.add_argument("--show", action="store_true")
    execution = parser.add_mutually_exclusive_group()
    execution.add_argument("--dry-run", action="store_true")
    execution.add_argument("--try", dest="try_command", action="store_true")
    parser.add_argument("--debug", action="store_true")
    info = parser.add_mutually_exclusive_group()
    info.add_argument("--version", action="store_true")
    info.add_argument("--model", action="store_true")
    info.add_argument("--models", action="store_true")
    info.add_argument("--changemodel", nargs="?", const="")
    parser.add_argument("--force-model", action="store_true")
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
        elif args.version:
            if args.request or args.try_command or args.dry_run or args.show or args.force_model or args.operation not in (None, "ai", "version"):
                parser.error("--version does not accept a request or another operation")
            args.operation = "version"
        elif args.changemodel is not None or args.models:
            if args.operation != "ai" or args.request or args.try_command or args.dry_run or args.show or args.force_model:
                parser.error("Use chameleon ai --models or --changemodel [TAG], without a request or execution options")
        elif (args.model or args.try_command or args.force_model) and args.operation != "ai":
            parser.error("Use these options after chameleon ai")
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        human("Cancelled.")
        return 130
    except (ProviderError, ValueError, OSError) as exc:
        logging.getLogger("chameleon").warning("Operation failed: %s", type(exc).__name__)
        if isinstance(exc, PermissionError):
            human(
                f"Windows denied access to {exc.filename or "the path"}. Use a user folder (Documents or Desktop) and check its permissions; regular files do not require an elevated terminal."
            )
        else:
            human(str(exc))
        return 1
    except Exception:
        logging.getLogger("chameleon").exception("Internal failure")
        if "--debug" in (argv or sys.argv[1:]):
            raise
        human("Chameleon encountered an error. Run \"chameleon doctor\" and check the local logs.")
        return 1
