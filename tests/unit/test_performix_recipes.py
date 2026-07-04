from neosentinel.telemetry.recipes import run_code_hotspots, run_memory_bandwidth


class TestPerformixRecipes:
    def test_code_hotspots_returns_hotspots(self):
        report = run_code_hotspots("node-002")
        assert report.recipe == "code_hotspots"
        assert report.node_id == "node-002"
        assert len(report.hotspots) >= 1
        assert report.sve2_utilization_pct == 29.0

    def test_memory_bandwidth_recipe(self):
        report = run_memory_bandwidth("node-002")
        assert report.recipe == "memory_bandwidth"
        assert report.dram_bandwidth_pct == 88.5
        assert report.cache_miss_rate_pct == 45.0

    def test_custom_runner(self):
        def runner(cmd: list[str]) -> str:
            assert "code_hotspots" in cmd
            return (
                "=== PMU Snapshot @ 2026-07-04T12:00:00Z ===\n"
                "node_id: node-001\n"
                "sve2_utilization_pct: 55.0\n"
                "dram_bandwidth_pct: 40.0\n"
                "cache_miss_rate_pct: 5.0\n"
            )

        report = run_code_hotspots("node-001", runner=runner)
        assert report.sve2_utilization_pct == 55.0
