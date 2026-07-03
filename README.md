# NeoSentinel v2.0

Autonomous cluster healing for ARM Graviton inference workloads.

## Week 0 Status

Foundation scaffold, frozen contracts in `neosentinel/contracts/`, and CI skeleton are in place. See [docs/infra/aws-3-node-provisioning.md](docs/infra/aws-3-node-provisioning.md) for the 3-node Graviton4 provisioning checklist.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Contracts

Shared boundary between the data/intelligence plane (Sahil) and control/experience plane (Divyansh). Do not modify without both owners signing off.

- `neosentinel/contracts/telemetry.py`
- `neosentinel/contracts/decision.py`
- `neosentinel/contracts/streams.py`
- `neosentinel/contracts/websocket.py`
- `neosentinel/contracts/openapi.yaml`
