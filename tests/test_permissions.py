from pathlib import Path

import pytest

from chameleon.core.config import Config, SafetyConfig, load_config, save_config
from chameleon.core.schemas import Action, Plan
from chameleon.safety.engine import Risk, RiskEngine


@pytest.mark.parametrize(
    "mode,script,confirmation",
    [
        ("read_only", False, True),
        ("balanced", False, True),
        ("developer", True, True),
        ("full", True, False),
    ],
)
def test_profiles_have_effective_permissions(mode: str, script: bool, confirmation: bool) -> None:
    policy = SafetyConfig(mode=mode)
    assert policy.permissions()["scripts"] == script and policy.confirms() == confirmation


@pytest.mark.parametrize(
    "command",
    [
        "echo x > file.txt",
        "dir & del file.txt",
        'python -c "print(1)"',
        "powershell -EncodedCommand YQ==",
        "curl https://example.com",
        "./script.ps1",
        "Remove-Item -LiteralPath file.txt",
        "dir & unknown-program",
        'Get-ChildItem | Where-Object {[IO.File]::Delete("x")}',
    ],
)
def test_read_only_blocks_mutation_and_opaque_code(command: str, tmp_path: Path) -> None:
    assert (
        RiskEngine(policy=SafetyConfig(mode="read_only")).command(command, tmp_path).level
        == Risk.BLOCKED
    )


@pytest.mark.parametrize(
    "command", ["type script.py", "type script.cmd", "Get-Content -LiteralPath script.ps1", "dir"]
)
def test_read_only_can_read_source_files(command: str, tmp_path: Path) -> None:
    assert (
        RiskEngine(policy=SafetyConfig(mode="read_only")).command(command, tmp_path).level
        == Risk.SAFE
    )


def test_custom_delete_permission_is_independent(tmp_path: Path) -> None:
    policy = SafetyConfig(mode="custom", allow_delete=False)
    risk = RiskEngine(policy=policy)
    assert (
        risk.action(Action(kind="create", path=str(tmp_path / "new.txt")), tmp_path).level
        == Risk.CONFIRM
    )
    assert (
        risk.action(Action(kind="delete", path=str(tmp_path / "old.txt")), tmp_path).level
        == Risk.BLOCKED
    )
    assert risk.command("del old.txt", tmp_path).level == Risk.BLOCKED
    assert risk.command('python -c "pass"', tmp_path).level == Risk.BLOCKED


@pytest.mark.parametrize(
    "command",
    [
        'python -c "print(1)"',
        "powershell -File example.ps1",
        "format Z:",
        "del C:\\Windows\\example.txt",
        "unknown-program",
    ],
)
def test_full_mode_has_no_application_block_or_confirmation(command: str, tmp_path: Path) -> None:
    # Assessment only: never execute these example commands.
    risk = RiskEngine(policy=SafetyConfig(mode="full"))
    plan = Plan(
        intent="execute",
        shell="cmd",
        summary="command",
        actions=[Action(kind="command", command=command)],
    )
    assert risk.assess(plan, tmp_path).level == Risk.SAFE
    assert (
        RiskEngine(policy=SafetyConfig(mode="developer")).assess(plan, tmp_path).level
        == Risk.CONFIRM
    )


def test_custom_script_permission_requires_all_effects(tmp_path: Path) -> None:
    policy = SafetyConfig(
        mode="custom", allow_scripts=True, allow_delete=False, allow_network=True, allow_system=True
    )
    assert RiskEngine(policy=policy).command('python -c "print(1)"', tmp_path).level == Risk.BLOCKED
    policy.allow_delete = True
    assert RiskEngine(policy=policy).command('python -c "print(1)"', tmp_path).level == Risk.CONFIRM


def test_access_settings_round_trip(tmp_path: Path) -> None:
    cfg = Config(
        safety=SafetyConfig(mode="custom", allow_delete=False), ai={"model": "qwen2.5:0.5b"}
    )
    save_config(cfg, tmp_path)
    restored, warning = load_config(tmp_path)
    assert restored == cfg and warning is None and restored.ai.command_only


def test_explicit_existing_script_uses_direct_local_invocation(tmp_path: Path) -> None:
    import asyncio

    from chameleon.core.context import Context
    from chameleon.core.engine import Engine

    (tmp_path / "hello.cmd").write_text("@echo SCRIPT_OK", encoding="ascii")
    for mode, expected in (
        ("balanced", Risk.BLOCKED),
        ("developer", Risk.CONFIRM),
        ("full", Risk.SAFE),
    ):
        cfg = Config(safety={"mode": mode})
        plan, risk = asyncio.run(
            Engine(cfg).plan("ejecuta el script hello.cmd", Context(cwd=str(tmp_path)))
        )
        assert plan.actions[0].command == 'call "hello.cmd"' and risk.level == expected
        assert plan.trace.source == "local"


def test_custom_network_and_write_switches_are_effective(tmp_path: Path) -> None:
    policy = SafetyConfig(mode="custom", allow_network=True, allow_write=False)
    risk = RiskEngine(policy=policy)
    assert risk.command("curl https://example.com", tmp_path).level == Risk.CONFIRM
    assert risk.command("curl -o file.txt https://example.com", tmp_path).level == Risk.BLOCKED
    policy.allow_write = True
    assert risk.command("curl -o file.txt https://example.com", tmp_path).level == Risk.CONFIRM
