from __future__ import annotations

import os
from typing import Any

import redis
from redis.cluster import RedisCluster


def create_redis_client(
    *,
    url: str | None = None,
    host: str | None = None,
    port: int | None = None,
    cluster: bool | None = None,
    decode_responses: bool = True,
    **kwargs: Any,
) -> redis.Redis | RedisCluster:
    resolved_url = url or os.environ.get("NEOSENTINEL_REDIS_URL")
    if cluster is not None:
        use_cluster = cluster
    else:
        use_cluster = os.environ.get("NEOSENTINEL_REDIS_CLUSTER", "0") == "1"

    if resolved_url:
        if use_cluster:
            return RedisCluster.from_url(resolved_url, decode_responses=decode_responses, **kwargs)
        return redis.Redis.from_url(resolved_url, decode_responses=decode_responses, **kwargs)

    resolved_host = host or os.environ.get("NEOSENTINEL_REDIS_HOST", "127.0.0.1")
    resolved_port = port or int(os.environ.get("NEOSENTINEL_REDIS_PORT", "6379"))

    if use_cluster:
        return RedisCluster(
            host=resolved_host,
            port=resolved_port,
            decode_responses=decode_responses,
            **kwargs,
        )
    return redis.Redis(
        host=resolved_host,
        port=resolved_port,
        decode_responses=decode_responses,
        **kwargs,
    )
