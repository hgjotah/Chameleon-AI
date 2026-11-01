import asyncio
import base64
import json
import os
from pathlib import Path

import pytest

from chameleon.core.command_validation import candidate_error
from chameleon.core.config import Config, SafetyConfig
from chameleon.core.context import Context, apply_shell_state, build_context
from chameleon.core.engine import Engine
from chameleon.core.intents import is_real_command, local_plan
from chameleon.llm.prompts import command_prompt
from chameleon.llm.shell_reference import cmd_argument_errors, command_heads, powershell_reference
from chameleon.safety.engine import Risk, RiskEngine


def test_no_task_answer_examples_in_command_prompt() -> None:
    for shell in ("cmd", "powershell", "pwsh"):
        prompt = command_prompt(shell)
        assert "ONLY" in prompt and "command" in prompt
        assert "green" not in prompt.lower() and "verde" not in prompt.lower()
        assert "hostname" not in prompt.lower() and "mkdir" not in prompt.lower()


def test_explicit_powershell_cmdlets_stay_native_before_module_autoload() -> None:
    ctx = Context(cwd="C:/", shell="powershell")
    assert is_real_command("Get-NetAdapter", ctx)
    assert is_real_command("Invoke-MyUserFunction x", ctx)
    assert not is_real_command("muestra la configuración de red", ctx)


def test_cmd_pipeline_heads_preserve_quoted_ampersands() -> None:
    assert command_heads('type "a & b.txt" | findstr "hello|there" & missing-tool') == [
        "type",
        "findstr",
        "missing-tool",
    ]


def test_native_documented_value_constraint_is_not_a_task_answer_table() -> None:
    reference = "TINT [attribute]\nTwo hexadecimal digits specify the attribute."
    assert cmd_argument_errors("TINT=green", reference)
    assert not cmd_argument_errors("TINT 0a", reference)
    assert not cmd_argument_errors("TINT", reference)
    assert not cmd_argument_errors("UNRELATED green", reference)


def test_forced_model_cannot_guess_ambiguous_source(tmp_path: Path) -> None:
    (tmp_path / "report.txt").touch()
    (tmp_path / "report.csv").touch()

    class NeverCalled:
        async def plan(self, *_):
            raise AssertionError("Ambiguity is an actual observation, not a model guess")

    plan, _ = asyncio.run(
        Engine(Config(ai={"prefer_model": True}), NeverCalled()).plan(
            "borra report", Context(cwd=str(tmp_path))
        )
    )
    assert plan.intent == "clarify" and len(plan.choices) == 2


def test_read_hidden_extension_in_named_known_folder(tmp_path: Path) -> None:
    downloads = tmp_path / "redirected downloads"
    downloads.mkdir()
    target = downloads / "report.txt"
    target.write_text("actual", encoding="utf-8")
    plan = local_plan(
        "lee report en Downloads",
        Context(cwd=str(tmp_path), known_directories={"Downloads": str(downloads)}),
    )
    assert plan and plan.actions[0].path == str(target)


def test_grounded_operands_allow_command_choice_but_reject_changed_destination(
    tmp_path: Path,
) -> None:
    ctx = Context(
        cwd=str(tmp_path),
        requested_action={
            "kind": "copy",
            "path": str(tmp_path / "a.txt"),
            "destination": str(tmp_path / "b.txt"),
        },
    )
    assert not candidate_error('copy "a.txt" "b.txt"', ctx)
    assert not candidate_error(
        "Copy-Item -LiteralPath 'a.txt' -Destination 'b.txt'",
        ctx.model_copy(update={"shell": "powershell"}),
    )
    assert candidate_error("copy a.txt wrong.txt", ctx)
    assert candidate_error("del a.txt", ctx)
    assert candidate_error("copy a.txt a b.txt", ctx)


def test_caller_metadata_cannot_change_policy_or_directory(tmp_path: Path) -> None:
    ctx = Context(cwd=str(tmp_path), permissions={"delete": False})
    encoded = base64.b64encode(
        json.dumps(
            {
                "edition": "Core",
                "language_mode": "ConstrainedLanguage",
                "commands": ["MySessionFunction"],
                "permissions": {"delete": True},
                "cwd": "C:/",
            }
        ).encode()
    ).decode()
    apply_shell_state(ctx, encoded)
    assert ctx.shell_edition == "Core" and ctx.language_mode == "ConstrainedLanguage"
    assert "mysessionfunction" in ctx.executables
    assert ctx.cwd == str(tmp_path) and not ctx.permissions["delete"]
    with pytest.raises(ValueError):
        apply_shell_state(ctx, "x" * 16385)


def test_compound_request_is_not_absorbed_as_creation_name(tmp_path: Path) -> None:
    assert (
        local_plan("crea un archivo a.txt y luego borra b.txt", Context(cwd=str(tmp_path))) is None
    )
    plan = local_plan('crea un archivo "a y luego borra b.txt"', Context(cwd=str(tmp_path)))
    assert plan and plan.actions[0].path.endswith("a y luego borra b.txt")


def test_filtered_delete_is_not_rejected_as_an_invented_literal_path(tmp_path: Path) -> None:
    ctx = Context(cwd=str(tmp_path))
    assert local_plan("borra todos los archivos *.log", ctx) is None
    target = tmp_path / "todas mis notas.txt"
    target.touch()
    plan = local_plan('borra "todas mis notas.txt"', ctx)
    assert plan and plan.actions[0].path == str(target)


@pytest.mark.parametrize(
    "command",
    [
        "color 02",
        "title Chameleon QA",
        "$Host.UI.RawUI.ForegroundColor = 'Green'",
        "$Host.UI.RawUI.WindowTitle = 'QA'",
    ],
)
def test_session_only_changes_respect_commands_capability(command: str) -> None:
    assert RiskEngine().command(command).level == Risk.SAFE
    assert RiskEngine(policy=SafetyConfig(mode="read_only")).command(command).level == Risk.BLOCKED


def test_console_allowlist_does_not_grant_script_execution() -> None:
    assert RiskEngine().command("color 02 & unknown-tool").level == Risk.BLOCKED
    assert (
        RiskEngine().command('$Host.UI.RawUI.WindowTitle = "$(Remove-Item important.txt)"').level
        == Risk.BLOCKED
    )


def test_literal_session_reads_do_not_require_arbitrary_script_permissions() -> None:
    policy = SafetyConfig(mode="read_only")
    assert RiskEngine(policy=policy).command("$env:COMPUTERNAME").level == Risk.SAFE
    assert RiskEngine(policy=policy).command("$PWD.Path").level == Risk.SAFE
    assert (
        RiskEngine(policy=policy).command("$env:COMPUTERNAME; Remove-Item x.txt").level
        == Risk.BLOCKED
    )


@pytest.mark.skipif(os.name != "nt", reason="Native Windows metadata")
def test_real_shell_context_and_environment_allowlist(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MY_API_TOKEN", "secret-not-context")
    ctx = build_context(tmp_path, "powershell")
    assert ctx.shell_version.startswith("5.1") and ctx.shell_edition == "Desktop"
    assert ctx.shell_executable.lower().endswith("powershell.exe")
    assert (
        "MY_API_TOKEN" not in ctx.environment and "secret-not-context" not in ctx.model_dump_json()
    )


@pytest.mark.skipif(os.name != "nt", reason="Native PowerShell AST")
def test_native_inspection_checks_pipeline_and_never_executes(tmp_path: Path) -> None:
    marker = tmp_path / "never-created.txt"
    command = f"Set-Content -LiteralPath '{marker}' -Value QA | Get-NotARealCmdlet"
    result = powershell_reference(command, Context(cwd=str(tmp_path), shell="powershell"))
    assert any("Get-NotARealCmdlet" in error for error in result["errors"])
    assert not marker.exists()
    bad = powershell_reference(
        "Get-Content -InventedParameter x", Context(cwd=str(tmp_path), shell="powershell")
    )
    assert bad["errors"], bad
    bare = powershell_reference("'C:\\Windows'", Context(cwd=str(tmp_path), shell="powershell"))
    assert bare["errors"]
    enum = powershell_reference(
        "$Host.UI.RawUI.ForegroundColor = 'NotARealColor'",
        Context(cwd=str(tmp_path), shell="powershell"),
    )
    assert enum["errors"]
