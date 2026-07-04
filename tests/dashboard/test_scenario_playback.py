import pytest

from neosentinel.dashboard.broadcaster import TelemetryBroadcaster
from neosentinel.dashboard.mock_feed import MockTelemetryFeed
from neosentinel.simulation.catalog import SCENARIOS


@pytest.mark.asyncio
async def test_scenario_fixture_playback_through_broadcaster() -> None:
    feed = MockTelemetryFeed()
    broadcaster = TelemetryBroadcaster(use_redis=False)
    events = feed.load_fixture("sve2_underutilization")
    sent: list[dict] = []

    class CaptureSocket:
        async def send_json(self, payload: dict) -> None:
            sent.append(payload)

    capture = CaptureSocket()
    broadcaster.active_connections.add(capture)
    for event in events:
        await broadcaster.broadcast(event)

    assert len(sent) == 5
    assert sent[0]["type"] == "metrics"
    assert sent[-1]["type"] == "audit"


@pytest.mark.parametrize("scenario_name", list(SCENARIOS.keys()))
def test_all_scenario_fixtures_validate(scenario_name: str) -> None:
    feed = MockTelemetryFeed()
    events = feed.load_fixture(scenario_name)
    assert len(events) >= 4
    types = {event["type"] for event in events}
    assert "metrics" in types
    assert "healing" in types
    assert "audit" in types
