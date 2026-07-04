from neosentinel.distributed.ray_tasks import (
    NODE_IDS,
    LocalRayTaskDispatcher,
    MockRayTaskDispatcher,
    create_ray_dispatcher,
)


class TestRayDispatch:
    def test_parallel_performix_recipes_all_nodes(self):
        dispatcher = LocalRayTaskDispatcher(max_workers=3)
        results = dispatcher.dispatch_performix_recipes(NODE_IDS, recipe="code_hotspots")
        assert len(results) == 3
        assert all(result.success for result in results)
        assert {result.node_id for result in results} == set(NODE_IDS)
        assert all(result.task == "performix:code_hotspots" for result in results)

    def test_memory_bandwidth_recipe_dispatch(self):
        dispatcher = LocalRayTaskDispatcher()
        results = dispatcher.dispatch_performix_recipes(("node-002",), recipe="memory_bandwidth")
        assert results[0].payload["recipe"] == "memory_bandwidth"

    def test_remote_config_apply(self):
        dispatcher = LocalRayTaskDispatcher()
        result = dispatcher.apply_remote_config("node-002", {"max_num_seqs": 128})
        assert result.success is True
        assert result.payload["applied"]["max_num_seqs"] == 128

    def test_remote_config_batch(self):
        dispatcher = LocalRayTaskDispatcher()
        results = dispatcher.apply_remote_config_batch(
            {
                "node-001": {"worker_threads": 4},
                "node-002": {"worker_threads": 6},
            }
        )
        assert len(results) == 2
        assert all(result.task == "apply_vllm_config" for result in results)

    def test_mock_dispatcher_records_calls(self):
        dispatcher = MockRayTaskDispatcher()
        dispatcher.dispatch_performix_recipes(NODE_IDS)
        dispatcher.apply_remote_config("node-002", {"enable_kleidiai": True})
        assert len(dispatcher.calls) == 2
        assert dispatcher.calls[0][0] == "performix"

    def test_create_dispatcher_defaults_to_local(self):
        dispatcher = create_ray_dispatcher(use_ray=False)
        results = dispatcher.dispatch_performix_recipes(("node-001",))
        assert len(results) == 1
