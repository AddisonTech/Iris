"""REST API tests over a pre-populated cache (no broker needed)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from iris.api import create_app
from iris.core import TopicCache


@pytest.fixture
def client():
    cache = TopicCache()
    cache.update("plant/line1/temp", 42.5, None)
    cache.update("plant/line1/mode", None, "AUTO")
    return TestClient(create_app(cache))


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["topics"] == 2


def test_topics(client):
    assert "plant/line1/temp" in client.get("/topics").json()["topics"]


def test_latest(client):
    r = client.get("/latest", params={"topic": "plant/line1/temp"})
    assert r.status_code == 200
    assert r.json()["value"] == 42.5


def test_latest_404(client):
    assert client.get("/latest", params={"topic": "nope"}).status_code == 404


def test_values(client):
    assert len(client.get("/values").json()["values"]) == 2
