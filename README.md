# NeoSentinel v2.0

Autonomous cluster healing for ARM Graviton inference workloads.

## Quickstart (5 minutes — offline / judges)

```bash
pip install -e ".[dev]"
neosentinel init
neosentinel doctor --mock
neosentinel start --serve --mock --no-open-browser
neosentinel simulate --scenario sve2_underutilization --speed 3
neosentinel report --output cluster_report.html
```

Open `http://localhost:8080` for the dashboard (mock WebSocket feed plays the SVE2 heal scenario).

## Live 3-Node Deploy (Week 7)

Provision 3× AWS Graviton4 (`c8g.4xlarge`) per [docs/infra/aws-3-node-provisioning.md](docs/infra/aws-3-node-provisioning.md), then:

**On each node** (bootstrap once):

```bash
curl -fsSL https://raw.githubusercontent.com/your-org/NeoSentinel/main/scripts/bootstrap-node.sh | bash
# or: bash scripts/bootstrap-node.sh
```

**On node-001** (control plane + Docker stack):

```bash
cd docker && docker compose up -d --build
export NEOSENTINEL_MOCK_MODE=0
export NEOSENTINEL_REDIS_URL=redis://127.0.0.1:6379
neosentinel run-orchestrator &
cd dashboard-ui && npm ci && npm run build
uvicorn neosentinel.dashboard.server:app --host 0.0.0.0 --port 8080
```

**On node-002 / node-003** (telemetry daemons):

```bash
export NEOSENTINEL_REDIS_URL=redis://<node-001-private-ip>:6379
neosentinel run-pipeline --node node-002   # or node-003
```

**Validate heal:**

```bash
neosentinel inject --node node-002 --anomaly sve2_underutilization --real
neosentinel doctor --live
neosentinel report --redis-host <node-001-ip> --output cluster_report.html
```

Set `NEOSENTINEL_NODE_HOSTS=node-001,node-002,node-003` in `~/.ssh/config` for `cluster-init --live-ssh` and live doctor SSH checks.

### Environment variables

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `NEOSENTINEL_MOCK_MODE` | `1` | `0` = dashboard reads live Redis |
| `NEOSENTINEL_REDIS_URL` | `redis://127.0.0.1:6379` | Redis endpoint |
| `NEOSENTINEL_REDIS_CLUSTER` | `0` | Set `1` for Redis Cluster mode |
| `NEOSENTINEL_SCENARIO` | `sve2_underutilization` | Mock feed scenario name |
| `NEOSENTINEL_NODE_HOSTS` | `node-001,node-002,node-003` | SSH hostnames for cluster-init / doctor |

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Docker Stack (local)

```bash
cd docker
docker compose up -d --build
curl http://localhost/health
```

See [docker/vllm/README.md](docker/vllm/README.md) for KleidiAI production build flags.

## Contracts

Shared boundary between the data/intelligence plane and control/experience plane. Do not modify without both owners signing off.

- `neosentinel/contracts/telemetry.py`
- `neosentinel/contracts/decision.py`
- `neosentinel/contracts/streams.py`
- `neosentinel/contracts/websocket.py`
- `neosentinel/contracts/openapi.yaml`
