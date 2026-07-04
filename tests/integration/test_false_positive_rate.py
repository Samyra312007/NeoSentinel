import pytest

from neosentinel.agent.decision_tree import evaluate_node
from neosentinel.agent.synthetic import SYNTHETIC_72HR_TICKS, HealthyTelemetryGenerator
from neosentinel.agent.tuning import (
    FALSE_POSITIVE_TARGET_PCT,
    measure_brain_false_positives,
    measure_decision_tree_false_positives,
    run_72hr_false_positive_audit,
)
from neosentinel.contracts.decision import ActionType

pytestmark = pytest.mark.slow


class TestFalsePositiveRate:
    def test_healthy_envelope_never_triggers_on_single_snapshot(self):
        generator = HealthyTelemetryGenerator(seed=1)
        snapshot = generator.generate_snapshot()
        for node in snapshot.nodes:
            candidate = evaluate_node(node)
            assert candidate.action == ActionType.NOOP

    def test_72hr_synthetic_decision_tree_below_2_percent(self):
        generator = HealthyTelemetryGenerator(seed=42)
        snapshots = list(generator.stream_72hr(ticks=SYNTHETIC_72HR_TICKS))
        assert len(snapshots) == 8640

        report = measure_decision_tree_false_positives(snapshots)
        assert report.total_ticks == 8640
        assert report.meets_target
        assert report.false_positive_rate_pct < FALSE_POSITIVE_TARGET_PCT

    def test_72hr_synthetic_brain_below_2_percent(self):
        report = run_72hr_false_positive_audit(seed=99, use_brain=True)
        assert report.total_ticks == SYNTHETIC_72HR_TICKS
        assert report.meets_target
        assert report.false_positive_rate_pct < FALSE_POSITIVE_TARGET_PCT

    def test_brain_false_positive_report_fields(self):
        generator = HealthyTelemetryGenerator(seed=7)
        snapshots = list(generator.stream_72hr(ticks=500))
        report = measure_brain_false_positives(snapshots)
        assert report.total_ticks == 500
        assert 0.0 <= report.false_positive_rate_pct <= 100.0
