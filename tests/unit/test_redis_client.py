"""redis client factory tests (closes the 0% coverage gap).

Construction of ``redis.Redis`` does not open a socket, so the non-cluster paths
are asserted for real by inspecting the resolved connection kwargs. The cluster
paths (which *would* connect) are exercised with a stub so no server is needed.
"""

from __future__ import annotations

import redis

from neosentinel.distributed import redis_client as rc


def _kwargs(client: redis.Redis) -> dict:
    return client.connection_pool.connection_kwargs


def test_defaults_to_localhost_non_cluster() -> None:
    client = rc.create_redis_client()
    assert isinstance(client, redis.Redis)
    assert _kwargs(client)["host"] == "127.0.0.1"
    assert _kwargs(client)["port"] == 6379


def test_explicit_host_and_port_override() -> None:
    client = rc.create_redis_client(host="10.0.0.5", port=6380)
    assert _kwargs(client)["host"] == "10.0.0.5"
    assert _kwargs(client)["port"] == 6380


def test_env_vars_resolve_host_and_port(monkeypatch) -> None:
    monkeypatch.setenv("NEOSENTINEL_REDIS_HOST", "redis.internal")
    monkeypatch.setenv("NEOSENTINEL_REDIS_PORT", "7001")
    client = rc.create_redis_client()
    assert _kwargs(client)["host"] == "redis.internal"
    assert _kwargs(client)["port"] == 7001


def test_url_builds_from_url(monkeypatch) -> None:
    client = rc.create_redis_client(url="redis://cache-host:6390/2")
    assert isinstance(client, redis.Redis)
    assert _kwargs(client)["host"] == "cache-host"
    assert _kwargs(client)["port"] == 6390


def test_env_url_is_used_when_no_arg(monkeypatch) -> None:
    monkeypatch.setenv("NEOSENTINEL_REDIS_URL", "redis://from-env:6391/0")
    client = rc.create_redis_client()
    assert _kwargs(client)["host"] == "from-env"
    assert _kwargs(client)["port"] == 6391


def test_cluster_flag_routes_to_cluster_constructor(monkeypatch) -> None:
    captured = {}

    class _StubCluster:
        def __init__(self, **kw):
            captured.update(kw)

    monkeypatch.setattr(rc, "RedisCluster", _StubCluster)
    client = rc.create_redis_client(host="node-a", port=7000, cluster=True)
    assert isinstance(client, _StubCluster)
    assert captured["host"] == "node-a"
    assert captured["port"] == 7000


def test_cluster_env_flag(monkeypatch) -> None:
    seen = {}

    class _StubCluster:
        @classmethod
        def from_url(cls, url, **kw):
            seen["url"] = url
            return cls()

    monkeypatch.setattr(rc, "RedisCluster", _StubCluster)
    monkeypatch.setenv("NEOSENTINEL_REDIS_CLUSTER", "1")
    client = rc.create_redis_client(url="redis://c:7000")
    assert isinstance(client, _StubCluster)
    assert seen["url"] == "redis://c:7000"
