# Iris

An **MQTT / Sparkplug B bridge** for the OT stack. Iris subscribes to a broker,
keeps the latest value per topic, exposes them over REST and as MCP tools for AI
agents, and can forward every reading to a [Clio](../Clio) historian.

Named for Iris, messenger of the gods — fitting for a message-bus bridge. It
mirrors the ModBridge shape (CLI + REST + MCP) for the pub/sub world.

## Status

Scaffold with a working MQTT ingest loop. Plain MQTT payloads (numbers, JSON
`{"value": ...}`, text) are parsed today. **Sparkplug B** topics (`spBv1.0/...`)
are detected and flagged; full protobuf payload decoding (via the Tahu schema)
is the next step.

## Run

```bash
pip install -r requirements.txt

# Subscribe and forward to Clio:
python -m iris subscribe --broker localhost --topic 'plant/#' --clio http://localhost:8010

# Bridge + REST API:
python -m iris serve --broker localhost --topic '#' --api-port 8011

# MCP server (owns its own subscription, exposes read tools to agents):
python -m iris.mcp_server
```

Configuration via flags, env (`IRIS_BROKER_HOST`, `IRIS_BROKER_PORT`,
`IRIS_TOPICS`, `IRIS_CLIO_URL`, `IRIS_SOURCE`), or `config.example.toml`.

## REST API

| Method | Path       | Purpose                              |
|--------|------------|--------------------------------------|
| GET    | `/health`  | Liveness + topic count               |
| GET    | `/topics`  | Topics seen since connect            |
| GET    | `/latest`  | Latest sample for a `topic`          |
| GET    | `/values`  | Latest sample for every topic        |

## MCP tools (read-only)

`list_topics`, `get_latest(topic)`, `read_all`. Publishing back to the broker is
a write path and is intentionally **not** exposed — consistent with the
disabled-by-default posture on writes elsewhere in the stack.

## Tests

```bash
pytest
```

## License

MIT © AddisonTech
