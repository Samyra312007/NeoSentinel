import os

import pytest

from neosentinel.telemetry.hardware import (
    HARDWARE_ENV_VAR,
    parse_and_validate_apx_sample,
    validate_graviton4_performix,
)
from neosentinel.telemetry.mock_performix import MockPerformix

requires_hardware = pytest.mark.skipif(
    os.environ.get(HARDWARE_ENV_VAR, "").strip() not in {"1", "true", "yes"},
    reason=f"Set {HARDWARE_ENV_VAR}=1 for real Graviton4 hardware validation",
)


class TestPerformixHardware:
    def test_parse_apx_sample_validates_sve2_counter(self):
        sample = MockPerformix("node-001", sve2_base=72.5, seed=1).to_apx_text()
        frame = parse_and_validate_apx_sample(sample, node_id="node-001")
        assert 0.0 <= frame.sve2_utilization_pct <= 100.0
        assert frame.node_id == "node-001"

    def test_injected_runner_passes_validation(self):
        sample = MockPerformix("node-002", sve2_base=81.0, seed=2).to_apx_text()

        def runner(_cmd):
            return sample

        result = validate_graviton4_performix(node_id="node-002", runner=runner)
        assert result.passed
        assert result.sve2_readable
        assert result.frame is not None
        assert result.frame.sve2_utilization_pct > 0.0

    def test_skipped_when_hardware_env_not_set(self):
        result = validate_graviton4_performix()
        if os.environ.get(HARDWARE_ENV_VAR, "").strip() not in {"1", "true", "yes"}:
            assert not result.available
            assert HARDWARE_ENV_VAR in result.message

    @requires_hardware
    def test_real_graviton4_sve2_counters_readable(self):
        result = validate_graviton4_performix(node_id="node-001")
        assert result.passed, result.message
        assert result.frame is not None
        assert result.sve2_readable
