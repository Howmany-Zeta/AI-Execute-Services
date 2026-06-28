# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Hook configuration schemas (§5.3–§5.4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CommandHookDefinition(BaseModel):
    """A hook that executes a subprocess without shell (§12.3)."""

    type: Literal["command"] = "command"
    command: str | list[str]
    timeout_seconds: int = Field(default=30, ge=1, le=600)
    matcher: str | None = None
    block_on_failure: bool = False
    priority: int = Field(default=0)
    """Higher priority runs first within an event; ties keep registration order."""

    @field_validator("command", mode="before")
    @classmethod
    def normalize_command(cls, value: str | list[str]) -> str | list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("command must be non-empty")
            return stripped
        if not value:
            raise ValueError("command list must be non-empty")
        return [str(part) for part in value]


class PromptHookDefinition(BaseModel):
    """A hook that asks the model to validate a condition."""

    type: Literal["prompt"] = "prompt"
    prompt: str
    model: str | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=600)
    matcher: str | None = None
    block_on_failure: bool = True
    priority: int = Field(default=0)


class HttpHookDefinition(BaseModel):
    """A hook that POSTs the event payload to an HTTP endpoint."""

    type: Literal["http"] = "http"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=600)
    matcher: str | None = None
    block_on_failure: bool = False
    priority: int = Field(default=0)


class AgentHookDefinition(BaseModel):
    """A hook that performs a deeper model-based validation."""

    type: Literal["agent"] = "agent"
    prompt: str
    model: str | None = None
    timeout_seconds: int = Field(default=60, ge=1, le=1200)
    matcher: str | None = None
    block_on_failure: bool = True
    priority: int = Field(default=0)


HookDefinition = CommandHookDefinition | PromptHookDefinition | HttpHookDefinition | AgentHookDefinition
