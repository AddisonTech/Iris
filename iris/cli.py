"""
iris/cli.py
CLI for the Iris MQTT bridge, mirroring the ModBridge command shape.

    iris subscribe --broker localhost --topic 'plant/#' --clio http://localhost:8010
    iris serve     --broker localhost --topic '#' --api-port 8011
"""
from __future__ import annotations

import argparse
import os
import threading
from typing import Optional


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--broker", default=os.environ.get("IRIS_BROKER_HOST", "localhost"))
    p.add_argument("--port", type=int, default=int(os.environ.get("IRIS_BROKER_PORT", "1883")))
    p.add_argument("--topic", action="append", dest="topics",
                   help="topic filter (repeatable); default '#'")
    p.add_argument("--clio", default=os.environ.get("IRIS_CLIO_URL", ""),
                   help="Clio historian URL to forward readings to (optional)")
    p.add_argument("--source", default=os.environ.get("IRIS_SOURCE", "iris"))


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="iris", description="Iris — MQTT/Sparkplug bridge for the OT stack."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("subscribe", help="subscribe and forward messages")
    _add_common(s)

    sv = sub.add_parser("serve", help="run the bridge plus a REST API")
    _add_common(sv)
    sv.add_argument("--api-host", default="127.0.0.1")
    sv.add_argument("--api-port", type=int, default=8011)

    args = parser.parse_args(argv)

    from iris.bridge import MqttBridge
    from iris.core import TopicCache

    cache = TopicCache()
    clio = None
    if args.clio:
        from iris.clientlib import ClioForwarder
        clio = ClioForwarder(args.clio)
    bridge = MqttBridge(cache, topics=args.topics or ["#"], clio_client=clio, source=args.source)

    if args.cmd == "subscribe":
        print(f"Iris subscribing to {args.broker}:{args.port} topics={bridge.topics}"
              + (f" -> Clio {args.clio}" if args.clio else ""))
        bridge.run(host=args.broker, port=args.port)
    elif args.cmd == "serve":
        import uvicorn
        from iris.api import create_app

        t = threading.Thread(target=bridge.run, kwargs={"host": args.broker, "port": args.port}, daemon=True)
        t.start()
        print(f"Iris bridge -> {args.broker}:{args.port}; REST on http://{args.api_host}:{args.api_port}")
        uvicorn.run(create_app(cache), host=args.api_host, port=args.api_port)


if __name__ == "__main__":
    main()
