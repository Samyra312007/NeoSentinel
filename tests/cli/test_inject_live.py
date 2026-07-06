import fakeredis

from neosentinel.cli.daemons import inject_live_anomaly
from neosentinel.contracts.streams import STREAM_PMU, STREAM_VLLM


def test_inject_live_seeds_redis(monkeypatch) -> None:
    client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setenv("NEOSENTINEL_REDIS_URL", "redis://127.0.0.1:6379")
    monkeypatch.setattr(
        "neosentinel.cli.daemons.create_redis_client",
        lambda **kwargs: client,
    )
    result = inject_live_anomaly("node-002", "sve2_underutilization")
    assert result["mode"] == "live"
    assert result["sve2_utilization_pct"] == 29.0
    assert client.xlen(STREAM_PMU) >= 3
    assert client.xlen(STREAM_VLLM) >= 3
