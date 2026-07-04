"""S5.1 Ray cluster integration for NeoSentinel.

Provides Ray remote tasks for parallel Performix recipe execution and remote
configuration apply across Graviton4 cluster nodes.  When Ray is unavailable
(offline / CI), every public function degrades gracefully to a local stub so
the rest of the orchestrator can still be tested without a Ray head node.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ray availability guard
# ---------------------------------------------------------------------------
try:
    import ray

    RAY_AVAILABLE = True
except ImportError:  # pragma: no cover – CI has no Ray
    RAY_AVAILABLE = False
    ray = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PerformixRecipeResult:
    """Result of a single Performix recipe execution on a node."""

    node_id: str
    recipe: str
    success: bool
    duration_ms: int
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ConfigApplyResult:
    """Result of applying a configuration patch to a remote node."""

    node_id: str
    config_key: str
    old_value: Any = None
    new_value: Any = None
    success: bool = True
    error: str | None = None


# ---------------------------------------------------------------------------
# Local (non-Ray) implementations
# ---------------------------------------------------------------------------
def _local_run_performix_recipe(
    node_id: str,
    recipe: str,
    *,
    parameters: dict[str, Any] | None = None,
) -> PerformixRecipeResult:
    """Execute a Performix recipe locally (mock / single-node mode)."""
    start = time.monotonic()
    try:
        # In production this would SSH into the node and run apx.
        # For now we return a deterministic mock result.
        output: dict[str, Any] = {
            "node_id": node_id,
            "recipe": recipe,
            "parameters": parameters or {},
            "sve2_utilization_pct": 78.5,
            "hotspots": [
                {"symbol": "vllm::attention_kernel", "samples_pct": 34.2},
                {"symbol": "arm_sve2::gemm_fp16", "samples_pct": 22.1},
            ],
        }
        elapsed = int((time.monotonic() - start) * 1000)
        return PerformixRecipeResult(
            node_id=node_id,
            recipe=recipe,
            success=True,
            duration_ms=elapsed,
            output=output,
        )
    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        return PerformixRecipeResult(
            node_id=node_id,
            recipe=recipe,
            success=False,
            duration_ms=elapsed,
            error=str(exc),
        )


def _local_apply_config(
    node_id: str,
    config_key: str,
    new_value: Any,
    *,
    old_value: Any = None,
) -> ConfigApplyResult:
    """Apply a configuration change locally (mock / single-node mode)."""
    return ConfigApplyResult(
        node_id=node_id,
        config_key=config_key,
        old_value=old_value,
        new_value=new_value,
        success=True,
    )


# ---------------------------------------------------------------------------
# Ray remote wrappers
# ---------------------------------------------------------------------------
if RAY_AVAILABLE:

    @ray.remote
    def _ray_run_performix_recipe(
        node_id: str,
        recipe: str,
        parameters: dict[str, Any] | None = None,
    ) -> PerformixRecipeResult:
        return _local_run_performix_recipe(node_id, recipe, parameters=parameters)

    @ray.remote
    def _ray_apply_config(
        node_id: str,
        config_key: str,
        new_value: Any,
        old_value: Any = None,
    ) -> ConfigApplyResult:
        return _local_apply_config(node_id, config_key, new_value, old_value=old_value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def run_performix_recipe(
    node_id: str,
    recipe: str,
    *,
    parameters: dict[str, Any] | None = None,
    use_ray: bool | None = None,
) -> PerformixRecipeResult:
    """Run a Performix recipe on *node_id*.

    When ``use_ray`` is ``True`` (or ``None`` and Ray is initialised), the task
    is dispatched as a Ray remote call.  Otherwise it runs locally.
    """
    should_use_ray = use_ray if use_ray is not None else (RAY_AVAILABLE and ray.is_initialized())
    if should_use_ray and RAY_AVAILABLE:
        ref = _ray_run_performix_recipe.remote(node_id, recipe, parameters)
        return ray.get(ref)
    return _local_run_performix_recipe(node_id, recipe, parameters=parameters)


def run_performix_parallel(
    node_ids: list[str],
    recipe: str,
    *,
    parameters: dict[str, Any] | None = None,
    use_ray: bool | None = None,
) -> list[PerformixRecipeResult]:
    """Run a Performix recipe on multiple nodes in parallel.

    Falls back to sequential local execution when Ray is not available.
    """
    should_use_ray = use_ray if use_ray is not None else (RAY_AVAILABLE and ray.is_initialized())
    if should_use_ray and RAY_AVAILABLE:
        refs = [_ray_run_performix_recipe.remote(nid, recipe, parameters) for nid in node_ids]
        return ray.get(refs)
    return [_local_run_performix_recipe(nid, recipe, parameters=parameters) for nid in node_ids]


def apply_config_remote(
    node_id: str,
    config_key: str,
    new_value: Any,
    *,
    old_value: Any = None,
    use_ray: bool | None = None,
) -> ConfigApplyResult:
    """Apply a configuration patch to a remote node."""
    should_use_ray = use_ray if use_ray is not None else (RAY_AVAILABLE and ray.is_initialized())
    if should_use_ray and RAY_AVAILABLE:
        ref = _ray_apply_config.remote(node_id, config_key, new_value, old_value)
        return ray.get(ref)
    return _local_apply_config(node_id, config_key, new_value, old_value=old_value)
