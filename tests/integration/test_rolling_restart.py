"""S5.4 tests — Rolling restart logic (node-002-first pattern).

Verifies the canonical restart ordering and edge cases like partial
node lists and empty input.
"""

from __future__ import annotations

from neosentinel.orchestrator.cluster import (
    ROLLING_RESTART_ORDER,
    ClusterSentinelOrchestrator,
    RestartStep,
    plan_rolling_restart,
)


class TestRollingRestart:
    def test_default_order_is_002_003_001(self) -> None:
        steps = plan_rolling_restart()
        node_order = [s.node_id for s in steps]
        assert node_order == ["node-002", "node-003", "node-001"]

    def test_steps_have_sequential_order_field(self) -> None:
        steps = plan_rolling_restart()
        for idx, step in enumerate(steps):
            assert step.order == idx
            assert step.status == "pending"

    def test_subset_preserves_canonical_order(self) -> None:
        steps = plan_rolling_restart(["node-001", "node-003"])
        node_order = [s.node_id for s in steps]
        # node-003 comes before node-001 in canonical order
        assert node_order == ["node-003", "node-001"]

    def test_single_node_restart(self) -> None:
        steps = plan_rolling_restart(["node-002"])
        assert len(steps) == 1
        assert steps[0].node_id == "node-002"
        assert steps[0].order == 0

    def test_empty_node_list(self) -> None:
        steps = plan_rolling_restart([])
        assert steps == []

    def test_unknown_node_excluded(self) -> None:
        steps = plan_rolling_restart(["node-099", "node-002"])
        assert len(steps) == 1
        assert steps[0].node_id == "node-002"

    def test_restart_step_is_dataclass(self) -> None:
        steps = plan_rolling_restart()
        for step in steps:
            assert isinstance(step, RestartStep)

    def test_constant_matches_spec(self) -> None:
        assert ROLLING_RESTART_ORDER == (
            "node-002",
            "node-003",
            "node-001",
        )


class TestOrchestratorPlanRestart:
    def test_orchestrator_delegates_to_planner(self) -> None:
        orch = ClusterSentinelOrchestrator()
        steps = orch.plan_restart()
        assert len(steps) == 3
        assert steps[0].node_id == "node-002"

    def test_orchestrator_partial_restart(self) -> None:
        orch = ClusterSentinelOrchestrator()
        steps = orch.plan_restart(["node-001", "node-002"])
        node_order = [s.node_id for s in steps]
        assert node_order == ["node-002", "node-001"]
