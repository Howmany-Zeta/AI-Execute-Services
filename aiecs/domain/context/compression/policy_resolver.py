# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Host-injected compression policy resolver (Epic 3 F3)."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from aiecs.domain.context.compression.policy import CompressionPolicy

if TYPE_CHECKING:
    from aiecs.domain.agent.models import AgentConfiguration


@runtime_checkable
class CompressionPolicyResolver(Protocol):
    """Select layer-specific ``CompressionPolicy`` (L2 vs L3)."""

    def __call__(
        self,
        *,
        layer: str,
        context: dict[str, Any],
        base_policy: CompressionPolicy,
    ) -> CompressionPolicy: ...


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def resolve_layer_compression_policy(
    layer: str,
    *,
    context: dict[str, Any],
    config: AgentConfiguration,
    base_policy: CompressionPolicy | None = None,
) -> CompressionPolicy:
    """Resolve policy for ``layer`` using context/config resolver when present."""
    from aiecs.domain.agent.models import resolve_compression_policy

    base = base_policy or resolve_compression_policy(config)
    resolver = context.get("compression_policy_resolver")
    if resolver is None:
        resolver = getattr(config, "compression_policy_resolver", None)
    if not callable(resolver):
        return base

    try:
        result = resolver(layer=layer, context=context, base_policy=base)
        result = await _maybe_await(result)
    except Exception:
        return base

    if isinstance(result, CompressionPolicy):
        return result
    if isinstance(result, dict):
        return CompressionPolicy(**result)
    return base
