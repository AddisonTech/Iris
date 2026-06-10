"""
iris/api.py
REST view over the live TopicCache. Read-only: Iris ingests from MQTT and
exposes the latest values; publishing back to the broker is a separate, gated
concern (see README).
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from iris.core import TopicCache


def create_app(cache: TopicCache) -> FastAPI:
    app = FastAPI(title="Iris MQTT Bridge", version="0.1.0")

    @app.get("/health")
    async def health():
        return {"status": "ok", "topics": len(cache.topics())}

    @app.get("/topics")
    async def topics():
        return {"topics": cache.topics()}

    @app.get("/latest")
    async def latest(topic: str):
        sample = cache.latest(topic)
        if sample is None:
            raise HTTPException(status_code=404, detail=f"no data for topic '{topic}'")
        return sample.to_dict()

    @app.get("/values")
    async def values():
        return {"values": [s.to_dict() for s in cache.all()]}

    return app
