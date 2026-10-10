from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ShellName = Literal["cmd", "powershell", "pwsh"]


class Action(BaseModel):
    """Typed operations avoid shell interpolation for paths and environment values."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["cd", "list", "find", "read", "delete", "clear", "env", "processes", "command"]
    path: str = Field(default="", max_length=4096)
    pattern: str = Field(default="*", max_length=256)
    recursive: bool = False
    min_size_bytes: int = Field(default=0, ge=0)
    modified_after: datetime | None = None
    file_type: Literal["any", "file", "directory"] = "any"
    limit: int = Field(default=20, ge=1, le=1000)
    command: str = Field(default="", max_length=8192)
    name: str = Field(default="", max_length=256)
    value: str = Field(default="", max_length=4096)

    @model_validator(mode="after")
    def valid_fields(self) -> "Action":
        for value in (self.path, self.pattern, self.command, self.name, self.value):
            if any(ord(c) < 32 for c in value):
                raise ValueError("Control characters are not permitted in actions")
        if self.kind == "command" and not self.command.strip():
            raise ValueError("Empty command")
        if self.kind in ("cd", "read", "delete") and not self.path:
            raise ValueError("Missing path")
        return self


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    intent: Literal["execute", "clarify", "explain", "error"]
    shell: ShellName
    actions: list[Action] = Field(default_factory=list, max_length=8)
    summary: str = Field(max_length=2000)
    confidence: float = Field(default=1.0, ge=0, le=1)
    model_risk: Literal["safe", "confirm", "blocked"] = "safe"
    requires_admin: bool = False
    choices: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def consistent(self) -> "Plan":
        if self.intent == "execute" and not self.actions:
            raise ValueError("Execution requires actions")
        if self.intent != "execute" and self.actions:
            raise ValueError("Non-execution plans cannot contain actions")
        return self


def generation_schema() -> dict:
    """Expose only applicable fields per action to constrained model decoding."""
    schema = Plan.model_json_schema()
    schema["required"] = list(schema["properties"])
    fields = schema["$defs"]["Action"]["properties"]
    variants = []
    by_kind = {
        "cd": ["path"],
        "list": ["path", "pattern", "recursive", "min_size_bytes", "modified_after", "file_type"],
        "find": ["path", "pattern", "recursive", "min_size_bytes", "modified_after", "file_type"],
        "read": ["path"],
        "delete": ["path", "recursive"],
        "clear": [],
        "env": ["name", "value"],
        "processes": ["limit"],
        "command": ["command"],
    }
    for kind, names in by_kind.items():
        properties = {"kind": {"type": "string", "const": kind}}
        properties.update({name: fields[name] for name in names})
        variants.append(
            {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            }
        )
    schema["$defs"]["Action"] = {"anyOf": variants}

    def compact(value: object) -> None:
        if isinstance(value, dict):
            value.pop("title", None)
            value.pop("default", None)
            for child in value.values():
                compact(child)
        elif isinstance(value, list):
            for child in value:
                compact(child)

    compact(schema)
    return schema
