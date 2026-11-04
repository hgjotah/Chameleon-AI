from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ShellName = Literal["cmd", "powershell", "pwsh"]


class Action(BaseModel):
    """Typed operations avoid shell interpolation for paths and environment values."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "cd",
        "list",
        "find",
        "read",
        "delete",
        "clear",
        "env",
        "processes",
        "command",
        "create",
        "mkdir",
        "copy",
        "move",
    ]
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
    content: str = Field(default="", max_length=65536)
    destination: str = Field(default="", max_length=4096)

    @model_validator(mode="after")
    def valid_fields(self) -> "Action":
        for value in (
            self.path,
            self.pattern,
            self.command,
            self.name,
            self.value,
            self.destination,
        ):
            if any(ord(c) < 32 for c in value):
                raise ValueError("Control characters are not permitted in actions")
        if self.kind == "command" and not self.command.strip():
            raise ValueError("Empty command")
        if "\x00" in self.content:
            raise ValueError("NUL is not permitted in file content")
        if (
            self.kind in ("cd", "read", "delete", "create", "mkdir", "copy", "move")
            and not self.path
        ):
            raise ValueError("Missing path")
        if self.kind in ("copy", "move") and not self.destination:
            raise ValueError("Missing destination")
        if self.destination and self.kind not in ("copy", "move"):
            raise ValueError("Destination is only valid for copy or move")
        return self


class InferenceTrace(BaseModel):
    source: Literal["local", "qwen"] = "local"
    model: str = ""
    duration_ms: int = 0
    output_tokens: int = 0
    calls: int = 0
    inspections: int = 0

    def label(self) -> str:
        return (
            "Local rule · no inference"
            if self.source == "local"
            else f"Ollama · {self.model} · {self.calls} call(s) · {self.output_tokens} tokens · {self.duration_ms / 1000:.1f} s · {self.inspections} inspection(s)"
        )


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    intent: Literal["execute", "inspect", "clarify", "explain", "error"]
    shell: ShellName
    actions: list[Action] = Field(default_factory=list, max_length=8)
    summary: str = Field(max_length=2000)
    confidence: float = Field(default=1.0, ge=0, le=1)
    model_risk: Literal["safe", "confirm", "blocked"] = "safe"
    requires_admin: bool = False
    choices: list[str] = Field(default_factory=list, max_length=20)
    trace: InferenceTrace = Field(default_factory=InferenceTrace)
    policy_token: str = Field(default="", max_length=4096)

    @model_validator(mode="after")
    def consistent(self) -> "Plan":
        if self.intent in ("execute", "inspect") and not self.actions:
            raise ValueError("Execution requires actions")
        if self.intent not in ("execute", "inspect") and self.actions:
            raise ValueError("Non-execution plans cannot contain actions")
        if self.intent == "inspect" and any(
            a.kind not in ("list", "find", "read", "processes") for a in self.actions
        ):
            raise ValueError("Inspection supports only read-only typed queries")
        return self


def generation_schema() -> dict:
    """Expose only applicable fields per action to constrained model decoding."""
    schema = Plan.model_json_schema()
    # The wire protocol restores these defaults after validation. Asking a small
    # model to generate advisory risk flags wastes tokens and suggests authority
    # that only the independent risk engine actually has.
    for name in ("version", "confidence", "model_risk", "requires_admin", "trace", "policy_token"):
        schema["properties"].pop(name)
    schema["properties"]["summary"]["maxLength"] = 240
    schema["properties"]["actions"]["maxItems"] = 4
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
        "create": ["path", "content"],
        "mkdir": ["path"],
        "copy": ["path", "destination"],
        "move": ["path", "destination"],
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
    schema["$defs"].pop("InferenceTrace", None)

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
