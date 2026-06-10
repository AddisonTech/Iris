"""Unit tests for Iris payload parsing, the topic cache, and the message handler."""
from __future__ import annotations

from iris.bridge import MqttBridge
from iris.core import TopicCache, is_sparkplug, parse_payload


# ── parse_payload ─────────────────────────────────────────────────────────────

def test_parse_float():
    assert parse_payload(b"42.5") == (42.5, None)


def test_parse_int():
    assert parse_payload(b"7") == (7.0, None)


def test_parse_json_numeric_value():
    assert parse_payload(b'{"value": 3.14}') == (3.14, None)


def test_parse_json_text_value():
    assert parse_payload(b'{"value": "AUTO"}') == (None, "AUTO")


def test_parse_plain_text():
    assert parse_payload(b"running") == (None, "running")


def test_parse_bool_json():
    assert parse_payload(b"true") == (None, "True")


def test_parse_empty():
    assert parse_payload(b"") == (None, None)


def test_sparkplug_detection():
    assert is_sparkplug("spBv1.0/Group/DDATA/Node")
    assert not is_sparkplug("plant/line1/temp")


# ── TopicCache ──────────────────────────────────────────────────────────────

def test_cache_keeps_latest_and_lists_topics():
    c = TopicCache()
    c.update("a", 1.0, None)
    c.update("a", 2.0, None)
    c.update("b", None, "x")
    assert c.latest("a").value == 2.0
    assert c.topics() == ["a", "b"]
    assert len(c.all()) == 2
    assert c.latest("missing") is None


# ── MqttBridge.on_message ─────────────────────────────────────────────────────

class _Msg:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload


def test_on_message_populates_cache():
    c = TopicCache()
    MqttBridge(c).on_message(None, None, _Msg("plant/temp", b"21.5"))
    assert c.latest("plant/temp").value == 21.5


def test_on_message_forwards_to_clio():
    c = TopicCache()
    pushed = []

    class FakeClio:
        def push(self, source, tag, value=None, value_text=None, quality="good", ts=None):
            pushed.append((source, tag, value, value_text))

    MqttBridge(c, clio_client=FakeClio(), source="iris").on_message(
        None, None, _Msg("plant/temp", b"21.5")
    )
    assert pushed == [("iris", "plant/temp", 21.5, None)]


def test_clio_failure_does_not_break_ingest():
    c = TopicCache()

    class BadClio:
        def push(self, *a, **k):
            raise RuntimeError("historian down")

    MqttBridge(c, clio_client=BadClio()).on_message(None, None, _Msg("t", b"1"))
    assert c.latest("t").value == 1.0  # cache still updated despite forward failure
