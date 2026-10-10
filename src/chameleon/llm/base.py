from abc import ABC, abstractmethod

from chameleon.core.context import Context
from chameleon.core.schemas import Plan


class ProviderError(RuntimeError):
    """A user-safe local inference failure."""


class LLMProvider(ABC):
    @abstractmethod
    async def plan(self, request: str, context: Context) -> Plan: ...
