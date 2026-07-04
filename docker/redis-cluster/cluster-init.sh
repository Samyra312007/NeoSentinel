#!/bin/sh
set -e

NODES="redis-node-1:6379 redis-node-2:6379 redis-node-3:6379 redis-node-4:6379 redis-node-5:6379 redis-node-6:6379"

for endpoint in $NODES; do
  host="${endpoint%%:*}"
  port="${endpoint##*:}"
  until redis-cli -h "$host" -p "$port" ping 2>/dev/null | grep -q PONG; do
    sleep 1
  done
done

if redis-cli -h redis-node-1 -p 6379 cluster info 2>/dev/null | grep -q "cluster_state:ok"; then
  echo "Redis cluster already initialized"
  exit 0
fi

redis-cli --cluster create $NODES --cluster-replicas 1 --cluster-yes
echo "Redis cluster initialized"
