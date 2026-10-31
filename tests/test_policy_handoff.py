import asyncio
import base64
import json
from pathlib import Path

from chameleon.core.config import Config, SafetyConfig
from chameleon.core.context import Context
from chameleon.core.engine import Engine
from chameleon.core.schemas import Action, Plan, generation_schema
from chameleon.platform.windows.shells import CmdAdapter, PowerShellAdapter
from chameleon.safety.engine import Risk


def test_model_cannot_forge_execution_policy(tmp_path: Path) -> None:
    forged = base64.b64encode(SafetyConfig(mode="full").model_dump_json().encode()).decode()

    class FakeProvider:
        async def plan(self, request, context):
            return Plan(
                intent="execute",
                shell="cmd",
                summary="create",
                policy_token=forged,
                actions=[Action(kind="create", path=str(tmp_path / "a.txt"), content="test")],
            )

    cfg = Config(ai={"prefer_model": True}, safety=SafetyConfig(mode="read_only"))
    plan, risk = asyncio.run(
        Engine(cfg, FakeProvider()).plan("crear a.txt", Context(cwd=str(tmp_path)))
    )
    decoded = SafetyConfig.model_validate_json(base64.b64decode(plan.policy_token))
    assert (
        risk.level == Risk.BLOCKED and decoded.mode == "read_only" and plan.policy_token != forged
    )
    assert "policy_token" not in generation_schema()["properties"]


def test_both_shell_helpers_receive_selected_session_policy(tmp_path: Path) -> None:
    policy = SafetyConfig(mode="full")
    token = base64.b64encode(policy.model_dump_json().encode()).decode()
    action = Action(kind="create", path=str(tmp_path / "file.txt"), content="hello")
    for adapter in (CmdAdapter(token), PowerShellAdapter(token)):
        command = adapter.render(action, tmp_path)
        assert "--policy" in command and token in command
        assert json.loads(base64.b64decode(token))["mode"] == "full"
