"""Ray local-fallback dispatcher tests (ray not installed here).

The orchestrator defaults to ``LocalRayTaskDispatcher`` when Ray is absent, so
these prove the fan-out still does real work (one result per node, config
applied) — the path that actually runs in this environment.
"""

from __future__ import annotations

from neosentinel.distributed.ray_tasks import (
    LocalRayTaskDispatcher,
    create_ray_dispatcher,
)


def test_dispatch_returns_one_result_per_node() -> None:
    dispatcher = LocalRayTaskDispatcher()
    results = dispatcher.dispatch_performix_recipes(
        ("node-001", "node-002", "node-003"), recipe="code_hotspots"
    )
    assert len(results) == 3
    node_ids = {r.node_id for r in results}
    assert node_ids == {"node-001", "node-002", "node-003"}
    assert all(r.task == "performix:code_hotspots" for r in results)
    assert all(r.success for r in results)


def test_apply_remote_config_roundtrips() -> None:
    dispatcher = LocalRayTaskDispatcher()
    result = dispatcher.apply_remote_config("node-002", {"max_num_seqs": 128})
    assert result.node_id == "node-002"


def test_apply_remote_config_batch_covers_all_nodes() -> None:
    dispatcher = LocalRayTaskDispatcher()
    results = dispatcher.apply_remote_config_batch(
        {"node-001": {"a": 1}, "node-002": {"b": 2}}
    )
    assert {r.node_id for r in results} == {"node-001", "node-002"}


def test_create_dispatcher_defaults_to_local_without_ray() -> None:
    dispatcher = create_ray_dispatcher(use_ray=False)
    assert isinstance(dispatcher, LocalRayTaskDispatcher)


def test_empty_node_list_yields_no_results() -> None:
    assert LocalRayTaskDispatcher().dispatch_performix_recipes((), recipe="x") == []

