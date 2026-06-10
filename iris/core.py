"""
iris/core.py
Transport-free core: payload parsing and the in-memory latest-value cache.

Kept independent of paho-mqtt so it can be unit-tested without a broker. The
bridge layer (iris/bridge.py) feeds parsed samples into a TopicCache; the REST
and MCP layers read from it.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Optional

# Sparkplug B topics live under this namespace. We flag them so callers know the
# payload is protobuf-encoded (full decode is a documented next step); plain
# MQTT JSON/text/number payloads are parsed directly.
SPARKPLUG_PREFIX = "spBv1.0/"


def is_sparkplug(topic: str) -> bool:
    return topic.startswith(SPARKPLUG_PREFIX)


def parse_payload(raw: bytes) -> tuple[Optional[float], Optional[str]]:
    """Best-effort parse of an MQTT payload into (value, value_text).

    Order: plain number -> JSON scalar -> JSON object with a 'value' field ->
    raw text. Numeric values populate `value`; everything else `value_text`.
    """
    if raw is None:
        return None, None
    text = raw.decode("utf-8", errors="replace").strip() if isinstance(raw, (bytes, bytearray)) else str(raw).strip()
    if text == "":
        return None, None

    try:
        return float(text), None
    except ValueError:
        pass

    try:
        obj = json.loads(text)
    except Exception:
        return None, text

    if isinstance(obj, bool):
        return None, str(obj)
    if isinstance(obj, (int, float)):
        return float(obj), None
    if isinstance(obj, dict) and "value" in obj:
        v = obj["value"]
        if isinstance(v, bool):
            return None, str(v)
        if isinstance(v, (int, float)):
            return float(v), None
        return None, str(v)
    return None, text


@dataclass
class Sample:
    topic: str
    value: Optional[float]
    value_text: Optional[str]
    ts: float  # UTC epoch seconds
    sparkplug: bool = False

    def to_dict(self) -> dict:
        from datetime import datetime, timezone
        return {
            "topic": self.topic,
            "value": self.value,
            "value_text": self.value_text,
            "ts": datetime.fromtimestamp(self.ts, tz=timezone.utc).isoformat(),
            "sparkplug": self.sparkplug,
        }


class TopicCache:
    """Thread-safe store of the latest Sample per topic."""

    def __init__(self) -> None:
        self._d: dict[str, Sample] = {}
        self._lock = threading.Lock()

    def update(
        self,
        topic: str,
        value: Optional[float],
        value_text: Optional[str],
        ts: Optional[float] = None,
    ) -> Sample:
        sample = Sample(
            topic=topic,
            value=value,
            value_text=value_text,
            ts=ts if ts is not None else time.time(),
            sparkplug=is_sparkplug(topic),
        )
        with self._lock:
            self._d[topic] = sample
        return sample

    def latest(self, topic: str) -> Optional[Sample]:
        with self._lock:
            return self._d.get(topic)

    def topics(self) -> list[str]:
        with self._lock:
            return sorted(self._d.keys())

    def all(self) -> list[Sample]:
        with self._lock:
            return list(self._d.values())
