from pathlib import Path

from chameleon.core.config import Config
from chameleon.core.context import Context
from chameleon.core.intents import local_plan
from chameleon.core.schemas import Plan
from chameleon.llm.base import LLMProvider, ProviderError
from chameleon.llm.ollama import OllamaProvider
from chameleon.safety.engine import Assessment, Risk, RiskEngine


class Engine:
    def __init__(self, config: Config, provider: LLMProvider | None = None) -> None:
        self.config = config
        self.provider = provider or OllamaProvider(config.ai)
        self.risk = RiskEngine(strict=config.safety.strict_mode)

    async def plan(self, request: str, context: Context) -> tuple[Plan, Assessment]:
        plan = local_plan(request, context)
        if plan is None:
            if not self.config.ai.enabled:
                raise ProviderError(
                    "IA desactivada. Las reglas locales y el terminal siguen disponibles."
                )
            plan = await self.provider.plan(request, context)
        current = Path(context.cwd)
        for action in plan.actions:
            if action.kind in ("cd", "list", "find", "read", "delete"):
                action.path = (
                    str((current / action.path).resolve()) if action.path else str(current)
                )
                if action.kind == "cd":
                    current = Path(action.path)
        self.risk = RiskEngine(context.system_directory, strict=self.config.safety.strict_mode)
        assessment = self.risk.assess(plan, Path(context.cwd))
        if assessment.requires_admin and not context.admin:
            assessment = Assessment(
                Risk.BLOCKED, "La acción requiere una terminal elevada. No se ejecutó nada.", True
            )
        return plan, assessment
