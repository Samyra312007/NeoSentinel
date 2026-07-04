from fastapi.testclient import TestClient
from neosentinel.dashboard.server import app


def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "dashboard"}


def test_websocket_endpoint():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"
