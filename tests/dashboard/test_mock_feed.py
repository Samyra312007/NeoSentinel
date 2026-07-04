import pytest

from neosentinel.dashboard.mock_feed import MockTelemetryFeed


def test_load_fixture_success():
    feed = MockTelemetryFeed()
    events = feed.load_fixture("sve2_underutilization")
    assert len(events) == 5
    event_types = [e["type"] for e in events]
    assert event_types == [
        "metrics",
        "agent_thought",
        "flame_graph",
        "healing",
        "audit",
    ]


def test_load_fixture_not_found():
    feed = MockTelemetryFeed()
    with pytest.raises(FileNotFoundError):
        feed.load_fixture("non_existent_scenario")


@pytest.mark.asyncio
async def test_stream_events():
    feed = MockTelemetryFeed()
    streamed = []
    async for event in feed.stream_events("sve2_underutilization", delay_sec=0):
        streamed.append(event)
    assert len(streamed) == 5
