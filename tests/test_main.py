import pytest

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_read_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Blind Stick Server is running"


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
