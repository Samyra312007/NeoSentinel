#!/usr/bin/env bash
set -euo pipefail

echo "=== NeoSentinel 3-minute demo script ==="
echo "SVE2 29% -> 79% | TTFT 312ms -> 131ms | Autonomous heal on Arm Graviton4"
echo

pip install -e ".[dev]" -q
neosentinel init
neosentinel doctor --mock

echo
echo "--- Offline judge path (no AWS) ---"
neosentinel simulate --scenario sve2_underutilization --speed 3
neosentinel report --output cluster_report.html
echo "Open http://localhost:8080 after: neosentinel start --serve --mock"

echo
echo "--- Live cluster path ---"
echo "1. docker compose up -d (on node-001)"
echo "2. neosentinel run-orchestrator &"
echo "3. neosentinel start --serve --live"
echo "4. neosentinel inject --node node-002 --anomaly sve2_underutilization --real"
echo "5. neosentinel doctor --live && neosentinel report --redis-host 127.0.0.1"
