# NeoSentinel v2.0

> **Autonomous cluster healing and real-time inference optimization for ARM Graviton4 AI workloads.**

NeoSentinel is a distributed, agentic reliability framework engineered to monitor, analyze, and autonomously remediate AI inference clusters running on ARM Graviton architecture (e.g., vLLM with KleidiAI INT4 optimizations). Under a strict **<5% CPU overhead budget**, NeoSentinel detects thermal throttling, SVE2 underutilization, memory bandwidth saturation, and KV-cache eviction floods, executing self-healing actions in real time.

---

## ⚡ Key Performance Metrics

| Metric | Degraded / Throttled State | Autonomous Healed State | Improvement |
| :--- | :--- | :--- | :--- |
| **SVE2 Vector Utilization** | 29% | **79%** | **+50%** efficiency |
| **Time-To-First-Token (TTFT)** | 312 ms | **131 ms** | **2.3x** faster response |
| **Mean Time to Heal (MTTH)** | Manual intervention | **< 90 seconds** | Zero-touch remediation |
| **Agent CPU Budget** | — | **< 5%** | Minimal host intrusion |

---

## 🚀 Project Roadmap & Status (Weeks 0–6 Complete)

NeoSentinel is developed across two parallel engineering tracks: the **Data/Intelligence Plane** (Sahil) and the **Control/Experience Plane** (Divyansh), unified by frozen Pydantic contracts.

- [x] **Week 0–1: Foundation & Stack Infrastructure**
  - 3-node AWS Graviton4 provisioning architecture and Docker deployment stack (`vLLM`, `Traefik`, `Redis`, `Ray`).
  - Frozen boundary contracts in `neosentinel/contracts/` (`telemetry`, `decision`, `streams`, `websocket`).
- [x] **Week 2: Real-Time Broadcaster & Dashboard Panels**
  - High-throughput WebSocket telemetry broadcasting with pub/sub Redis adapters.
  - Multi-panel React/Vite dashboard visualizer featuring real-time node health metrics and timeline charts.
- [x] **Week 3: Autonomous Agent UX & Decision Reasoning**
  - Grammar-constrained LLM agent reasoning (via `llama.cpp`) with verifiable decision trees.
  - Live "Agent Thought" streaming in the UI, exposing the step-by-step diagnostic chain of thought.
- [x] **Week 4: Action Executor & GitOps Audit Trails**
  - Safe, idempotent action execution engine with checkpointing and automated rollback triggers.
  - Automated GitOps audit commits logging every self-healing decision and state change.
- [x] **Week 5: Distributed Cluster Orchestrator & Ray Dispatch**
  - Cross-node anomaly correlation engine (`ClusterSentinelOrchestrator`) and Ray task dispatching.
  - Quorum-based voting consensus (2/3 majority required for destructive or cluster-wide actions).
  - Canonical rolling restart workflows (prioritizing `node-002` first).
- [x] **Week 6: Experience & Backend Hardening**
  - Comprehensive simulation CLI scenarios (`sve2_underutilization`, `thermal_throttling`, `kv_eviction_flood`).
  - False-positive detection tuning, high-concurrency load testing, and automated HTML report generation API.

---

## 🏁 Quickstart (5 Minutes)

Experience the entire autonomous self-healing workflow locally without requiring AWS hardware using deterministic simulation fixtures.

### 1. Install SDK & CLI
```bash
pip install -e ".[dev]"
neosentinel init
neosentinel doctor --mock
```

### 2. Run Autonomous Healing Simulation
Simulate an SVE2 vector underutilization event at 3x speed and generate an HTML audit report:
```bash
neosentinel start --no-serve --no-open-browser
neosentinel simulate --scenario sve2_underutilization --speed 3
neosentinel report --output cluster_report.html
```

### 3. Replay Telemetry Streams
Replay recorded thermal throttling timelines for offline debugging or demonstrations:
```bash
neosentinel replay --stream thermal_throttling --speed 10
```

---

## 🖥️ Dashboard UI (React + Vite)

Launch the interactive web visualizer to monitor cluster telemetry, live agent thoughts, and quorum voting:

```bash
cd dashboard-ui
npm ci
npm run dev
```
Open your browser to `http://localhost:5173` to view the live dashboard.

---

## 🐳 Docker Cluster Stack

Start the complete 3-node local emulation stack featuring vLLM (with KleidiAI production build flags), Traefik load balancer, Redis pub/sub broker, and Ray cluster orchestration:

```bash
cd docker
docker compose up -d --build
curl http://localhost/health
```

See [docker/vllm/README.md](docker/vllm/README.md) for specialized KleidiAI INT4 compilation flags and container configurations.

---

## 🛠️ Development & Testing

NeoSentinel enforces strict quality gates: zero merges without passing tests and comprehensive validation.

```bash
# Run unit and integration tests
pytest

# Run linter and static checks
ruff check .
```

### Core Architecture & Seams
- **`neosentinel/contracts/`**: Immutable boundary schemas shared between data and UI planes (`telemetry.py`, `decision.py`, `streams.py`, `websocket.py`, `openapi.yaml`).
- **`neosentinel/telemetry/performix.py`**: Injectable telemetry runner allowing hardware counter simulation and PMU profiling without physical ARM access.
- **`neosentinel/distributed/`**: Ray cluster task dispatching and Redis client wrappers for distributed orchestration.
- **`neosentinel/orchestration/`**: Quorum consensus algorithms and self-healing action execution engines.

---

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
