import time
from pathlib import Path

import fakeredis

from neosentinel.cli.daemons import inject_live_anomaly
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.streams import STREAM_DECISIONS, STREAM_HEALING
from neosentinel.distributed.streams import TelemetryPipeline
from neosentinel.orchestrator.cluster import ClusterSentinelOrchestrator


class TestLiveHealE2E:
    def test_sve2_heal_under_90s(self, tmp_path: Path, monkeypatch) -> None:
        client = fakeredis.FakeRedis(decode_responses=True)
        monkeypatch.setenv("NEOSENTINEL_REDIS_URL", "redis://127.0.0.1:6379")
        monkeypatch.setattr(
            "neosentinel.cli.daemons.create_redis_client",
            lambda **kwargs: client,
        )

        inject_live_anomaly("node-002", "sve2_underutilization")

        pipeline = TelemetryPipeline(client)
        orchestrator = ClusterSentinelOrchestrator(
            pipeline=pipeline,
            audit_root=tmp_path / "audit",
            checkpoint_root=tmp_path / "checkpoints",
        )

        started = time.monotonic()
        result = orchestrator.run_cycle()
        elapsed = time.monotonic() - started

        assert result is not None
        assert result.decision.action == ActionType.TRIGGER_REQUANTIZE
        assert result.executed is True
        assert result.heal_outcome is not None
        after = result.heal_outcome.result.after
        assert after.sve2_utilization_pct >= 79.0
        assert after.ttft_p99_ms <= 135.0
        assert elapsed < 90.0
        assert client.xlen(STREAM_DECISIONS) >= 1
        assert client.xlen(STREAM_HEALING) >= 1
        assert result.heal_outcome.commit_sha is not None
