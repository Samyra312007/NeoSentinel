from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Protocol

from neosentinel.telemetry.recipes import (
    run_code_hotspots,
    run_memory_bandwidth,
)

NODE_IDS = ("node-001", "node-002", "node-003")


@dataclass(frozen=True)
class RayTaskResult:
    node_id: str
    task: str
    success: bool
    payload: dict[str, Any]


def _run_recipe(node_id: str, recipe: str) -> RayTaskResult:
    if recipe == "memory_bandwidth":
        report = run_memory_bandwidth(node_id)
    else:
        report = run_code_hotspots(node_id)
    return RayTaskResult(
        node_id=node_id,
        task=f"performix:{recipe}",
        success=True,
        payload=report.to_dict(),
    )


def _apply_config(node_id: str, config: dict[str, Any]) -> RayTaskResult:
    return RayTaskResult(
        node_id=node_id,
        task="apply_vllm_config",
        success=True,
        payload={"applied": config},
    )


class RayTaskDispatcher(Protocol):
    def dispatch_performix_recipes(
        self,
        node_ids: tuple[str, ...],
        *,
        recipe: str = "code_hotspots",
    ) -> list[RayTaskResult]: ...

    def apply_remote_config(
        self,
        node_id: str,
        config: dict[str, Any],
    ) -> RayTaskResult: ...

    def apply_remote_config_batch(
        self,
        configs: dict[str, dict[str, Any]],
    ) -> list[RayTaskResult]: ...


@dataclass
class LocalRayTaskDispatcher:
    max_workers: int = 3

    def dispatch_performix_recipes(
        self,
        node_ids: tuple[str, ...],
        *,
        recipe: str = "code_hotspots",
    ) -> list[RayTaskResult]:
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(_run_recipe, node_id, recipe): node_id for node_id in node_ids
            }
            results: list[RayTaskResult] = []
            for future in as_completed(futures):
                results.append(future.result())
        return sorted(results, key=lambda item: item.node_id)

    def apply_remote_config(
        self,
        node_id: str,
        config: dict[str, Any],
    ) -> RayTaskResult:
        return _apply_config(node_id, config)

    def apply_remote_config_batch(
        self,
        configs: dict[str, dict[str, Any]],
    ) -> list[RayTaskResult]:
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(_apply_config, node_id, config): node_id
                for node_id, config in configs.items()
            }
            results = [future.result() for future in as_completed(futures)]
        return sorted(results, key=lambda item: item.node_id)


@dataclass
class MockRayTaskDispatcher:
    calls: list[tuple[str, tuple[str, ...] | str, dict[str, Any]]] = field(
        default_factory=list,
    )

    def dispatch_performix_recipes(
        self,
        node_ids: tuple[str, ...],
        *,
        recipe: str = "code_hotspots",
    ) -> list[RayTaskResult]:
        self.calls.append(("performix", node_ids, {"recipe": recipe}))
        return [_run_recipe(node_id, recipe) for node_id in node_ids]

    def apply_remote_config(
        self,
        node_id: str,
        config: dict[str, Any],
    ) -> RayTaskResult:
        self.calls.append(("config", node_id, config))
        return _apply_config(node_id, config)

    def apply_remote_config_batch(
        self,
        configs: dict[str, dict[str, Any]],
    ) -> list[RayTaskResult]:
        self.calls.append(("config_batch", tuple(configs), {}))
        return [_apply_config(node_id, config) for node_id, config in configs.items()]


def create_ray_dispatcher(*, use_ray: bool = False) -> RayTaskDispatcher:
    if not use_ray:
        return LocalRayTaskDispatcher()
    try:
        import ray

        if not ray.is_initialized():
            ray.init(address="auto", ignore_reinit_error=True)

        @ray.remote
        def remote_recipe(node_id: str, recipe: str) -> dict[str, Any]:
            result = _run_recipe(node_id, recipe)
            return {
                "node_id": result.node_id,
                "task": result.task,
                "success": result.success,
                "payload": result.payload,
            }

        @ray.remote
        def remote_config(node_id: str, config: dict[str, Any]) -> dict[str, Any]:
            result = _apply_config(node_id, config)
            return {
                "node_id": result.node_id,
                "task": result.task,
                "success": result.success,
                "payload": result.payload,
            }

        class ClusterRayDispatcher:
            def dispatch_performix_recipes(
                self,
                node_ids: tuple[str, ...],
                *,
                recipe: str = "code_hotspots",
            ) -> list[RayTaskResult]:
                refs = [remote_recipe.remote(nid, recipe) for nid in node_ids]
                raw = ray.get(refs)
                return [
                    RayTaskResult(
                        node_id=item["node_id"],
                        task=item["task"],
                        success=item["success"],
                        payload=item["payload"],
                    )
                    for item in sorted(raw, key=lambda x: x["node_id"])
                ]

            def apply_remote_config(
                self,
                node_id: str,
                config: dict[str, Any],
            ) -> RayTaskResult:
                item = ray.get(remote_config.remote(node_id, config))
                return RayTaskResult(**item)

            def apply_remote_config_batch(
                self,
                configs: dict[str, dict[str, Any]],
            ) -> list[RayTaskResult]:
                refs = [
                    remote_config.remote(node_id, config)
                    for node_id, config in configs.items()
                ]
                raw = ray.get(refs)
                return [RayTaskResult(**item) for item in sorted(raw, key=lambda x: x["node_id"])]

        return ClusterRayDispatcher()
    except Exception:
        return LocalRayTaskDispatcher()
