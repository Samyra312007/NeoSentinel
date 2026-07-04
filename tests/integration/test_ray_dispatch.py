"""S5.1 tests — Ray task dispatch (local fallback mode).

We test the *local* code path exclusively since CI has no Ray cluster.
The public API is designed so ``use_ray=False`` exercises the same logic.
"""

from __future__ import annotations

from neosentinel.distributed.ray_tasks import (
    ConfigApplyResult,
    PerformixRecipeResult,
    apply_config_remote,
    run_performix_parallel,
    run_performix_recipe,
)


class TestRunPerformixRecipe:
    def test_single_recipe_returns_result(self) -> None:
        result = run_performix_recipe("node-001", "code_hotspots", use_ray=False)
        assert isinstance(result, PerformixRecipeResult)
        assert result.node_id == "node-001"
        assert result.recipe == "code_hotspots"
        assert result.success is True
        assert result.error is None
        assert result.duration_ms >= 0

    def test_result_output_contains_sve2(self) -> None:
        result = run_performix_recipe("node-002", "memory_bandwidth", use_ray=False)
        assert "sve2_utilization_pct" in result.output
        assert isinstance(result.output["hotspots"], list)

    def test_parallel_dispatch_returns_all_nodes(self) -> None:
        nodes = ["node-001", "node-002", "node-003"]
        results = run_performix_parallel(nodes, "code_hotspots", use_ray=False)
        assert len(results) == 3
        returned_ids = {r.node_id for r in results}
        assert returned_ids == set(nodes)
        assert all(r.success for r in results)

    def test_parameters_forwarded(self) -> None:
        params = {"depth": 5, "threshold": 0.1}
        result = run_performix_recipe(
            "node-001",
            "code_hotspots",
            parameters=params,
            use_ray=False,
        )
        assert result.output["parameters"] == params


class TestApplyConfigRemote:
    def test_apply_config_success(self) -> None:
        result = apply_config_remote(
            "node-001",
            "vllm.max_batch_size",
            64,
            old_value=32,
            use_ray=False,
        )
        assert isinstance(result, ConfigApplyResult)
        assert result.success is True
        assert result.node_id == "node-001"
        assert result.config_key == "vllm.max_batch_size"
        assert result.old_value == 32
        assert result.new_value == 64

    def test_apply_config_default_old_value(self) -> None:
        result = apply_config_remote(
            "node-003",
            "ray.num_cpus",
            8,
            use_ray=False,
        )
        assert result.old_value is None
        assert result.new_value == 8
