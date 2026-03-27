# influxdb-1x-mcp

MCP server providing read-only access to **InfluxDB 1.x** (InfluxQL) for AI assistants like Claude.

## Features

- Execute arbitrary InfluxQL `SELECT` and `SHOW` queries
- List measurements with optional regex filter
- List tag values (e.g. all `entity_id` in a measurement)
- Connection ping / health check
- Read-only: only `SELECT` and `SHOW` queries allowed

## Installation

Requires Python 3.10+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/coolexer/influxdb_mcp
cd influxdb_mcp
uv sync
```

## Configuration (Claude Desktop)

Add to `claude_desktop_config.json`:

```json
"influxdb-1x": {
  "command": "uv",
  "args": [
    "--directory", "C:\\path\\to\\influxdb_mcp",
    "run", "influxdb-1x-mcp"
  ],
  "env": {
    "UV_LINK_MODE": "copy",
    "INFLUXDB_HOST": "192.168.1.100",
    "INFLUXDB_PORT": "8086",
    "INFLUXDB_DATABASE": "homeassistant"
  }
}
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `INFLUXDB_HOST` | `localhost` | InfluxDB host |
| `INFLUXDB_PORT` | `8086` | InfluxDB port |
| `INFLUXDB_DATABASE` | `homeassistant` | Default database |
| `INFLUXDB_USERNAME` | _(none)_ | Username (optional) |
| `INFLUXDB_PASSWORD` | _(none)_ | Password (optional) |

## Tools

| Tool | Description |
|---|---|
| `influx_ping` | Test connection, returns server version |
| `influx_show_measurements` | List all measurements, optional regex filter |
| `influx_show_tag_values` | List tag values for a measurement (e.g. all entity_ids) |
| `influx_query` | Execute any InfluxQL SELECT or SHOW query |

## Example Queries

```sql
-- All temperature sensors in Home Assistant
SHOW TAG VALUES FROM "°C" WITH KEY = "entity_id"

-- Boiler supply temperature last 24h, 5min averages
SELECT mean("value") FROM "°C"
WHERE "entity_id" = 'kotelnaia_kotel_tdeg_tn'
AND time > now() - 24h
GROUP BY time(5m)

-- Pump power last 6 hours
SELECT mean("value") FROM "W"
WHERE "entity_id" =~ /nasos/
AND time > now() - 6h
GROUP BY time(5m), "entity_id"
```

## License

MIT
