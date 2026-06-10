"""
iris/bridge.py
MQTT subscriber that feeds a TopicCache and (optionally) forwards each reading
to a Clio historian.

paho-mqtt is imported lazily inside `run()` so the class — and its `on_message`
handler — can be unit-tested without paho installed or a broker running.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from iris.core import TopicCache, parse_payload

logger = logging.getLogger("iris.bridge")


class MqttBridge:
    def __init__(
        self,
        cache: TopicCache,
        topics: Optional[list[str]] = None,
        clio_client: Any = None,
        source: str = "iris",
    ) -> None:
        self.cache = cache
        self.topics = topics or ["#"]
        self.clio = clio_client
        self.source = source

    # Called by paho on each message; signature matches both paho v1 and v2.
    def on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        value, value_text = parse_payload(msg.payload)
        sample = self.cache.update(msg.topic, value, value_text)
        if self.clio is not None:
            try:
                self.clio.push(
                    self.source, msg.topic, value=value, value_text=value_text
                )
            except Exception as exc:  # never let a historian outage kill the loop
                logger.warning("Clio forward failed for %s: %s", msg.topic, exc)
        logger.debug("rx %s -> value=%s text=%s", msg.topic, sample.value, sample.value_text)

    def _on_connect(self, client: Any, *args: Any, **kwargs: Any) -> None:
        # *args absorbs the differing paho v1/v2 connect callback signatures.
        for t in self.topics:
            client.subscribe(t)
            logger.info("subscribed to %s", t)

    def run(self, host: str = "localhost", port: int = 1883, keepalive: int = 60) -> None:
        import paho.mqtt.client as mqtt

        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  # paho >= 2.0
        except Exception:
            client = mqtt.Client()  # paho 1.x
        client.on_connect = self._on_connect
        client.on_message = self.on_message
        client.connect(host, port, keepalive)
        client.loop_forever()
