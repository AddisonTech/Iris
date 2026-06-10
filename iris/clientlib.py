"""
iris/clientlib.py
Minimal forwarder that pushes readings to a Clio historian. Self-contained
(just httpx) so Iris does not need Clio installed as a package.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx


class ClioForwarder:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def push(
        self,
        source: str,
        tag: str,
        value: Optional[float] = None,
        value_text: Optional[str] = None,
        quality: str = "good",
        ts: Optional[str] = None,
    ) -> Any:
        payload = {
            "source": source,
            "tag": tag,
            "value": value,
            "value_text": value_text,
            "quality": quality,
            "ts": ts,
        }
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(f"{self.base_url}/readings", json=payload)
            r.raise_for_status()
            return r.json()
