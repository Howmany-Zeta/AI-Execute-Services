# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Hook execution engine (§5.1.3, §12.3)."""

from __future__ import annotations

import asyncio
import fnmatch
import json
import os
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.hooks.schemas import (
    AgentHookDefinition,
    CommandHookDefinition,
    HookDefinition,
    HttpHookDefinition,
    PromptHookDefinition,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult, HookResult

_DEFAULT_EVENT_TIMEOUT_SECONDS = 60


class SupportsHookPrompt(Protocol):
    """Minimal LLM client surface for prompt/agent hooks."""

    async def complete_hook_prompt(self, *, prompt: str, model: str | None, max_tokens: int) -> str: ...


@dataclass
class AgentHookExecutionContext:
    """Context passed into hook execution."""

    cwd: Path
    default_model: str = ""
    api_client: SupportsHookPrompt | None = None
    hook_allowed_http_hosts: frozenset[str] = field(default_factory=frozenset)
    hook_env_allowlist: frozenset[str] = field(default_factory=frozenset)
    event_timeout_seconds: int = _DEFAULT_EVENT_TIMEOUT_SECONDS


class AgentHookExecutor:
    """Execute hooks for lifecycle events."""

    def __init__(self, registry: AgentHookRegistry, context: AgentHookExecutionContext) -> None:
        self._registry = registry
        self._context = context

    def update_registry(self, registry: AgentHookRegistry) -> None:
        self._registry = registry

    async def execute_event(self, event: AgentHookEvent, payload: dict[str, Any]) -> AggregatedHookResult:
        """Execute all matching hooks for an event serially (§5.1.3, §12.2)."""
        results: list[HookResult] = []
        deadline = time.monotonic() + self._context.event_timeout_seconds

        for hook in self._registry.get_hooks(event):
            if not _matches_hook(hook, payload):
                continue
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                results.append(
                    HookResult(
                        hook_type=hook.type,
                        success=False,
                        blocked=True,
                        reason=(f"event hook chain exceeded " f"{self._context.event_timeout_seconds}s budget"),
                    )
                )
                break
            effective_timeout = min(float(hook.timeout_seconds), remaining)
            if isinstance(hook, CommandHookDefinition):
                result = await self._run_command_hook(hook, event, payload, timeout_seconds=effective_timeout)
            elif isinstance(hook, HttpHookDefinition):
                result = await self._run_http_hook(hook, event, payload, timeout_seconds=effective_timeout)
            elif isinstance(hook, PromptHookDefinition):
                result = await self._run_prompt_like_hook(
                    hook,
                    event,
                    payload,
                    agent_mode=False,
                    timeout_seconds=effective_timeout,
                )
            elif isinstance(hook, AgentHookDefinition):
                result = await self._run_prompt_like_hook(
                    hook,
                    event,
                    payload,
                    agent_mode=True,
                    timeout_seconds=effective_timeout,
                )
            else:
                continue
            results.append(result)
        return AggregatedHookResult(results=results)

    async def _run_command_hook(
        self,
        hook: CommandHookDefinition,
        event: AgentHookEvent,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> HookResult:
        argv = _command_argv(hook.command)
        env = _minimal_hook_env(event, payload, self._context.hook_env_allowlist)
        stdin_payload = json.dumps(payload, ensure_ascii=True).encode("utf-8")

        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(self._context.cwd),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except OSError as exc:
            return HookResult(
                hook_type=hook.type,
                success=False,
                blocked=hook.block_on_failure,
                reason=str(exc),
            )

        hook_timeout = timeout_seconds if timeout_seconds is not None else float(hook.timeout_seconds)
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin_payload),
                timeout=hook_timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return HookResult(
                hook_type=hook.type,
                success=False,
                blocked=hook.block_on_failure,
                reason=f"command hook timed out after {hook_timeout}s",
            )

        output = "\n".join(
            part
            for part in (
                stdout.decode("utf-8", errors="replace").strip(),
                stderr.decode("utf-8", errors="replace").strip(),
            )
            if part
        )
        success = process.returncode == 0
        fields: dict[str, Any] = {}
        if success and output:
            fields = _extract_hook_fields(_try_parse_json_object(output))
        return _hook_result_from_fields(
            hook.type,
            success=success,
            output=output,
            blocked=hook.block_on_failure and not success,
            reason=output or f"command hook failed with exit code {process.returncode}",
            metadata={"returncode": process.returncode},
            fields=fields,
        )

    async def _run_http_hook(
        self,
        hook: HttpHookDefinition,
        event: AgentHookEvent,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> HookResult:
        host = urlparse(hook.url).hostname
        if not host or host not in self._context.hook_allowed_http_hosts:
            return HookResult(
                hook_type=hook.type,
                success=False,
                blocked=hook.block_on_failure,
                reason=f"http host not allowed: {host!r}",
            )
        hook_timeout = timeout_seconds if timeout_seconds is not None else float(hook.timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=hook_timeout) as client:
                response = await client.post(
                    hook.url,
                    json={"event": event.value, "payload": payload},
                    headers=hook.headers,
                )
            success = response.is_success
            output = response.text
            fields = _extract_hook_fields(_try_parse_json_object(output)) if success else {}
            return _hook_result_from_fields(
                hook.type,
                success=success,
                output=output,
                blocked=hook.block_on_failure and not success,
                reason=output or f"http hook returned {response.status_code}",
                metadata={"status_code": response.status_code},
                fields=fields,
            )
        except Exception as exc:
            return HookResult(
                hook_type=hook.type,
                success=False,
                blocked=hook.block_on_failure,
                reason=str(exc),
            )

    async def _run_prompt_like_hook(
        self,
        hook: PromptHookDefinition | AgentHookDefinition,
        event: AgentHookEvent,
        payload: dict[str, Any],
        *,
        agent_mode: bool,
        timeout_seconds: float | None = None,
    ) -> HookResult:
        if self._context.api_client is None:
            return HookResult(
                hook_type=hook.type,
                success=False,
                blocked=hook.block_on_failure,
                reason="prompt/agent hooks require an api_client in execution context",
            )

        prompt = _inject_arguments(hook.prompt, payload)
        prefix = "You are validating whether a hook condition passes in AIEcs. " 'Return strict JSON: {"ok": true} or {"ok": false, "reason": "..."}.'
        if agent_mode:
            prefix += " Be more thorough and reason over the payload before deciding."

        hook_timeout = timeout_seconds if timeout_seconds is not None else float(hook.timeout_seconds)
        try:
            text = await asyncio.wait_for(
                self._context.api_client.complete_hook_prompt(
                    prompt=f"{prefix}\n\n{prompt}",
                    model=hook.model or self._context.default_model or None,
                    max_tokens=512,
                ),
                timeout=hook_timeout,
            )
        except asyncio.TimeoutError:
            return HookResult(
                hook_type=hook.type,
                success=False,
                blocked=hook.block_on_failure,
                reason=f"prompt hook timed out after {hook_timeout}s",
            )
        except Exception as exc:
            return HookResult(
                hook_type=hook.type,
                success=False,
                blocked=hook.block_on_failure,
                reason=str(exc),
            )

        parsed = _parse_hook_json(text)
        fields = _extract_hook_fields(parsed)
        if parsed["ok"]:
            return _hook_result_from_fields(
                hook.type,
                success=True,
                output=text,
                fields=fields,
            )
        return _hook_result_from_fields(
            hook.type,
            success=False,
            output=text,
            blocked=hook.block_on_failure,
            reason=str(parsed.get("reason", "hook rejected the event")),
            fields=fields,
        )


def _matches_hook(hook: HookDefinition, payload: dict[str, Any]) -> bool:
    matcher = getattr(hook, "matcher", None)
    if not matcher:
        return True
    subject = str(payload.get("tool_name") or payload.get("prompt") or payload.get("event") or "")
    return fnmatch.fnmatch(subject, matcher)


def _inject_arguments(template: str, payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=True)
    return template.replace("$ARGUMENTS", serialized)


def _try_parse_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {}


def _extract_hook_fields(parsed: dict[str, Any]) -> dict[str, Any]:
    """Extract §17 hook output fields from parsed JSON."""
    fields: dict[str, Any] = {}
    modified_output = parsed.get("modified_output")
    if isinstance(modified_output, str):
        fields["modified_output"] = modified_output
    updated_mcp = parsed.get("updated_mcp_output")
    if isinstance(updated_mcp, str):
        fields["updated_mcp_output"] = updated_mcp
    updated_input = parsed.get("updated_input")
    if isinstance(updated_input, dict):
        fields["updated_input"] = updated_input
    permission_decision = parsed.get("permissionDecision") or parsed.get("permission_decision")
    if isinstance(permission_decision, str):
        fields["permission_decision"] = permission_decision.strip().lower()
    additional_context = parsed.get("additionalContext") or parsed.get("additional_context")
    if isinstance(additional_context, str) and additional_context.strip():
        fields["additional_context"] = additional_context.strip()
    continue_val = parsed.get("continue")
    if continue_val is False:
        fields["continue_allowed"] = False
    elif continue_val is True:
        fields["continue_allowed"] = True
    prevent = parsed.get("preventContinuation") or parsed.get("prevent_continuation")
    if prevent is True:
        fields["prevent_continuation"] = True
    if parsed.get("blocked") is True:
        fields["continue_allowed"] = False
    return fields


def _hook_result_from_fields(
    hook_type: str,
    *,
    success: bool,
    output: str = "",
    blocked: bool = False,
    reason: str = "",
    metadata: dict[str, Any] | None = None,
    fields: dict[str, Any] | None = None,
) -> HookResult:
    parsed = fields or {}
    hook_blocked = blocked or parsed.get("continue_allowed") is False
    return HookResult(
        hook_type=hook_type,
        success=success,
        output=output,
        blocked=hook_blocked,
        reason=reason or parsed.get("reason", ""),
        metadata=metadata or {},
        modified_output=parsed.get("modified_output"),
        updated_input=parsed.get("updated_input"),
        permission_decision=parsed.get("permission_decision"),
        updated_mcp_output=parsed.get("updated_mcp_output"),
        additional_context=parsed.get("additional_context"),
        continue_allowed=parsed.get("continue_allowed"),
        prevent_continuation=parsed.get("prevent_continuation"),
    )


def _parse_hook_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and isinstance(parsed.get("ok"), bool):
            return parsed
    except json.JSONDecodeError:
        pass
    lowered = text.strip().lower()
    if lowered in {"ok", "true", "yes"}:
        return {"ok": True}
    return {"ok": False, "reason": text.strip() or "hook returned invalid JSON"}


def _command_argv(command: str | list[str]) -> list[str]:
    if isinstance(command, list):
        if not command:
            raise ValueError("command list must be non-empty")
        return [str(part) for part in command]
    return shlex.split(command, posix=True)


def _minimal_hook_env(
    event: AgentHookEvent,
    payload: dict[str, Any],
    allowlist: frozenset[str],
) -> dict[str, str]:
    """Construct minimal env without inheriting parent secrets (§12.3)."""
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "AIECS_HOOK_EVENT": event.value,
        "AIECS_HOOK_PAYLOAD": json.dumps(payload, ensure_ascii=True),
    }
    for key in ("HOME", "TMPDIR", "TEMP", "TMP"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    for key in allowlist:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    return env
