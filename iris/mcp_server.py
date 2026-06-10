"""
iris/mcp_server.py
MCP server exposing live MQTT data to AI agents.

Like Hermes, the MCP server owns its own subscription: on startup it spins up an
MqttBridge in a background thread (configured via env) that keeps a TopicCache
warm, and the tools read from that cache. Tools are READ-ONLY — publishing to
the broker would be a write path and is intentionally not exposed here.

Start:
    python -m iris.mcp_server

Environment:
    IRIS_BROKER_HOST   MQTT broker host (default: localhost)
    IRIS_BROKER_PORT   MQTT broker port (default: 1883)
    IRIS_TOPICS        Comma-separated topic filters (default: #)
    IRIS_CLIO_URL      If set, forward readings to this Clio historian
    IRIS_SOURCE        Source label for forwarded readings (default: iris)
"""
from __future__ import annotations

import os
import threading
from typing import Any

from fastmcp import FastMCP

from iris.bridge import MqttBridge
from iris.core import TopicCache

mcp = FastMCP("iris")
cache = TopicCache()
_started = False
_start_lock = threading.Lock()


def _start_bridge_once() -> None:
    global _started
    with _start_lock:
        if _started:
            return
        clio = None
        clio_url = os.environ.get("IRIS_CLIO_URL", "").strip()
        if clio_url:
            from iris.clientlib import ClioForwarder
            clio = ClioForwarder(clio_url)
        topics = [t.strip() for t in os.environ.get("IRIS_TOPICS", "#").split(",") if t.strip()]
        bridge = MqttBridge(cache, topics=topics, clio_client=clio,
                            source=os.environ.get("IRIS_SOURCE", "iris"))
        host = os.environ.get("IRIS_BROKER_HOST", "localhost")
        port = int(os.environ.get("IRIS_BROKER_PORT", "1883"))
        thread = threading.Thread(target=bridge.run, kwargs={"host": host, "port": port}, daemon=True)
        thread.start()
        _started = True


@mcp.tool()
def list_topics() -> dict[str, Any]:
    """List MQTT topics seen since the bridge connected."""
    _start_bridge_once()
    return {"topics": cache.topics()}


@mcp.tool()
def get_latest(topic: str) -> dict[str, Any]:
    """Get the latest value received on an MQTT topic.

    Args:
        topic: Exact topic string (e.g. 'plant/line1/temp')
    """
    _start_bridge_once()
    sample = cache.latest(topic)
    return sample.to_dict() if sample else {"topic": topic, "error": "no data yet"}


@mcp.tool()
def read_all() -> dict[str, Any]:
    """Get the latest value for every topic seen so far."""
    _start_bridge_once()
    return {"values": [s.to_dict() for s in cache.all()]}


if __name__ == "__main__":
    _start_bridge_once()
    mcp.run()
