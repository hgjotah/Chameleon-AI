import asyncio
import base64
import re
from collections.abc import Callable
from pathlib import Path

from chameleon.core.config import Config
from chameleon.core.context import Context
from chameleon.core.inspection import inspect_action
from chameleon.core.intents import local_plan, resolve_path, resolve_reference
from chameleon.core.schemas import InferenceTrace, Plan
from chameleon.llm.base import LLMProvider, ProviderError
from chameleon.llm.ollama import OllamaProvider
from chameleon.safety.engine import Assessment, Risk, RiskEngine


class Engine:
    def __init__(
        self,
        config: Config,
        provider: LLMProvider | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config
        self.provider = provider or OllamaProvider(config.ai, progress=progress)
        self.risk = RiskEngine(strict=config.safety.strict_mode, policy=config.safety)
        self.progress = progress or (lambda _: None)

    async def plan(self, request: str, context: Context) -> tuple[Plan, Assessment]:
        local = local_plan(request, context)
        if local and local.intent == "execute" and len(local.actions) == 1:
            action = local.actions[0]
            if action.kind in ("create", "mkdir", "copy", "move"):
                target = Path(action.destination or action.path)
                if target.exists():
                    local = Plan(
                        intent="error",
                        shell=context.shell,
                        summary="El destino ya existe y la petición no solicita sobrescribirlo. Usa otro nombre o pide expresamente la sustitución.",
                    )
        # Missing/ambiguous literal paths are observations, not an invitation for
        # a forced model to guess a different file.
        plan = (
            local
            if local and local.intent in ("clarify", "error")
            else None
            if self.config.ai.prefer_model
            else local
        )
        if plan is None:
            if not self.config.ai.enabled:
                raise ProviderError(
                    "IA desactivada. Las reglas locales y el terminal siguen disponibles."
                )
            trace = InferenceTrace(source="qwen")
            context = context.model_copy(deep=True)
            context.permissions = self.config.safety.permissions()
            if not context.permissions["read"]:
                context.entries = []
                context.evidence = []
                context.observed_output = ""
                context.recent = []
            if (
                local
                and local.intent == "execute"
                and len(local.actions) == 1
                and local.actions[0].kind
                in ("create", "mkdir", "copy", "move", "delete", "read", "cd", "clear")
            ):
                context.action_kind_hint = local.actions[0].kind
            if local and local.intent == "execute":
                for action in local.actions:
                    if context.permissions["read"] and action.path and Path(action.path).exists():
                        target = Path(action.path)
                        context.evidence.append(
                            {
                                "kind": "stat",
                                "role": "source",
                                "path": str(target),
                                "exists": True,
                                "is_file": target.is_file(),
                                "ok": True,
                            }
                        )
                        trace.inspections += 1
            if self.config.ai.command_only:
                if local and local.intent == "execute" and len(local.actions) == 1:
                    action = local.actions[0]
                    context.requested_action = {
                        key: str(value)
                        for key, value in action.model_dump().items()
                        if key in ("kind", "path", "destination", "content") and value
                    }
            context.needs_verified_observation = bool(
                re.search(
                    r"(?:qu[eé] (?:contiene|hay|dice)|cu[aá]ntos?|existe|contenido|contents?|how many|does .+ exist|summari[sz]e|resume|explica|explain).*(?:archivos?|files?|carpeta|folder|\.\w{1,5}\b)|(?:qu[eé] (?:contiene|dice)|contents? of)\b",
                    request,
                    re.I,
                )
            )
            # A clearly named summary target can be read directly: avoid spending
            # a model round merely asking it to emit a read of that same file.
            summary_target = re.match(
                r"""\s*(?:resume|summari[sz]e)\s+(?:el archivo\s+|the file\s+)?("[^"]+"|'[^']+'|[^\s,;]+\.[\w]{1,5})(?:\s|$)""",
                request,
                re.I,
            )
            if (
                context.needs_verified_observation
                and summary_target
                and not self.config.ai.command_only
                and context.permissions["read"]
                and (not self.config.safety.strict_mode or self.config.safety.mode == "full")
            ):
                from chameleon.core.schemas import Action

                target, matches = resolve_reference(summary_target[1], context)
                if not matches and target.is_file():
                    context.evidence.append(
                        await asyncio.to_thread(
                            inspect_action, Action(kind="read", path=str(target)), context
                        )
                    )
                    trace.inspections += 1
            try:
                async with asyncio.timeout(self.config.ai.timeout):
                    for _ in range(3):
                        self.progress(
                            "QWEN RESPONDIENDO" if context.evidence else "QWEN CONSULTANDO"
                        )
                        plan = await self.provider.plan(request, context)
                        trace.model = plan.trace.model or self.config.ai.model
                        trace.calls += plan.trace.calls or 1
                        trace.duration_ms += plan.trace.duration_ms
                        trace.output_tokens += plan.trace.output_tokens
                        if plan.intent != "inspect":
                            if (
                                plan.intent == "explain"
                                and context.needs_verified_observation
                                and not any(e.get("ok") for e in context.evidence)
                            ):
                                raise ProviderError(
                                    "Qwen devolvió una respuesta sobre archivos sin comprobarlos. No se presenta como un hecho; indica la ruta o pide leer el archivo."
                                )
                            plan.trace = trace
                            break
                        if self.config.safety.strict_mode and self.config.safety.mode != "full":
                            raise ProviderError(
                                "El modo estricto no permite inspección automática. Usa una consulta explícita para leer el archivo o carpeta."
                            )
                        # Any tool request enters the observation/answer phase,
                        # including wording not covered by the initial heuristic.
                        context.needs_verified_observation = True
                        for action in plan.actions:
                            from chameleon.safety.permissions import denied

                            forbidden = denied(action, self.config.safety)
                            if forbidden:
                                raise ProviderError(forbidden)
                            self.progress("QWEN COMPROBANDO ARCHIVO")
                            result = await asyncio.to_thread(inspect_action, action, context)
                            context.evidence.append(result)
                            trace.inspections += 1
                    else:
                        raise ProviderError(
                            "Qwen solicitó demasiadas consultas. No se realizó ningún cambio; concreta la petición."
                        )
            except TimeoutError as exc:
                raise ProviderError(
                    "La consulta a Qwen superó el tiempo límite. No se realizó ningún cambio; aumenta el timeout en Ajustes → IA o concreta la petición."
                ) from exc
        current = Path(context.cwd)
        for action in plan.actions:
            if action.kind in (
                "cd",
                "list",
                "find",
                "read",
                "delete",
                "create",
                "mkdir",
                "copy",
                "move",
            ):
                location = context.model_copy(update={"cwd": str(current)})
                if action.kind in ("delete", "read", "copy", "move"):
                    target, matches = resolve_reference(action.path, location)
                    if matches:
                        plan = Plan(
                            intent="clarify",
                            shell=context.shell,
                            summary="El nombre corresponde a varios archivos. Selecciona la ruta exacta.",
                            choices=[str(p) for p in matches[:20]],
                            trace=plan.trace,
                        )
                        break
                    action.path = str(target)
                else:
                    action.path = (
                        str(resolve_path(action.path, location)) if action.path else str(current)
                    )
                if action.kind == "cd":
                    current = Path(action.path)
            if action.destination:
                action.destination = str(
                    resolve_path(
                        action.destination, context.model_copy(update={"cwd": str(current)})
                    )
                )
        self.risk = RiskEngine(
            context.system_directory,
            strict=self.config.safety.strict_mode,
            policy=self.config.safety,
        )
        if plan.intent == "execute" and any(a.kind == "delete" for a in plan.actions):
            plan.summary = "Propuesta de eliminación: " + "; ".join(
                a.path for a in plan.actions if a.kind == "delete"
            )
        elif plan.intent == "execute" and any(
            a.kind in ("create", "mkdir", "copy", "move") for a in plan.actions
        ):
            plan.summary = "Cambios propuestos, pendientes de confirmación: " + "; ".join(
                a.kind + " " + a.path for a in plan.actions
            )
        assessment = self.risk.assess(plan, Path(context.cwd))
        if assessment.requires_admin and not context.admin:
            assessment = Assessment(
                Risk.BLOCKED, "La acción requiere una terminal elevada. No se ejecutó nada.", True
            )
        # This execution snapshot is always authored by the app, never accepted
        # from model JSON. File helpers must use the same selected session policy.
        plan.policy_token = base64.b64encode(
            self.config.safety.model_dump_json().encode("utf-8")
        ).decode("ascii")
        return plan, assessment
