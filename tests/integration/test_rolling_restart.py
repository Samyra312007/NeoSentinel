from neosentinel.distributed.ray_tasks import MockRayTaskDispatcher
from neosentinel.orchestrator.restart import (
    ROLLING_RESTART_ORDER,
    execute_rolling_restart,
    plan_rolling_restart,
)


class TestRollingRestart:
    def test_node_002_first_order(self):
        plan = plan_rolling_restart()
        assert plan.order == ROLLING_RESTART_ORDER
        assert plan.order[0] == "node-002"
        assert plan.order[1] == "node-003"
        assert plan.order[2] == "node-001"

    def test_execute_rolling_restart_sequence(self):
        plan = plan_rolling_restart()
        restarted: list[str] = []

        execute_rolling_restart(
            plan,
            restart_fn=lambda node_id: restarted.append(node_id),
        )

        assert restarted == ["node-002", "node-003", "node-001"]
        assert plan.is_complete is True

    def test_rolling_restart_with_ray_config_apply(self):
        plan = plan_rolling_restart()
        ray = MockRayTaskDispatcher()

        execute_rolling_restart(
            plan,
            restart_fn=lambda node_id: ray.apply_remote_config(
                node_id,
                {"rolling_restart": True},
            ),
        )

        config_calls = [call for call in ray.calls if call[0] == "config"]
        assert [call[1] for call in config_calls] == list(ROLLING_RESTART_ORDER)
