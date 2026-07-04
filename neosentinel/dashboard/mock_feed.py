import asyncio
import json
from pathlib import Path
from typing import Any, AsyncGenerator

from pydantic import TypeAdapter

from neosentinel.contracts.websocket import WebSocketEvent

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "scenarios" / "fixtures"

_event_adapter = TypeAdapter(WebSocketEvent)


class MockTelemetryFeed:
    """Emits contract-valid WebSocket events from scenario JSON fixtures."""

    def __init__(self, fixtures_dir: Path | str | None = None) -> None:
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else FIXTURES_DIR

    def load_fixture(self, scenario_name: str) -> list[dict[str, Any]]:
        """Load and validate events from a scenario JSON file."""
        file_path = self.fixtures_dir / f"{scenario_name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Fixture scenario '{scenario_name}' not found at {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_events = json.load(f)

        validated_events = []
        for item in raw_events:
            # Validate against frozen Pydantic contract
            event_obj = _event_adapter.validate_python(item)
            validated_events.append(event_obj.model_dump(mode="json"))

        return validated_events

    async def stream_events(
        self, scenario_name: str, delay_sec: float = 0.1
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Asynchronously yield contract-valid events with simulated delay."""
        events = self.load_fixture(scenario_name)
        for event in events:
            yield event
            if delay_sec > 0:
                await asyncio.sleep(delay_sec)
