from abc import ABC, abstractmethod
from pathlib import Path

from chameleon.core.schemas import Action


class PlatformAdapter(ABC):
    @abstractmethod
    def known_directories(self) -> dict[str, str]: ...

    @abstractmethod
    def is_admin(self) -> bool: ...

    @abstractmethod
    def system_directory(self) -> str: ...


class ShellAdapter(ABC):
    @abstractmethod
    def render(self, action: Action, cwd: Path) -> str: ...


class PtyBackend(ABC):
    @abstractmethod
    def write(self, data: str) -> None: ...

    @abstractmethod
    def read(self) -> str: ...

    @abstractmethod
    def resize(self, rows: int, cols: int) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
