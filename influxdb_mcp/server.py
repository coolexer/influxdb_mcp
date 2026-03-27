"""
InfluxDB 1.x MCP Server — read-only InfluxQL query access.
Configuration via environment variables:
  INFLUXDB_HOST     — host (default: localhost)
  INFLUXDB_PORT     — port (default: 8086)
  INFLUXDB_DATABASE — database name (default: homeassistant)
  INFLUXDB_USERNAME — username (optional)
  INFLUXDB_PASSWORD — password (optional)
"""

import os
import json
import sys
from typing import Any

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

# ── Config from environment ──────────────────────────────────────────────────
HOST     = os.environ.get("INFLUXDB_HOST", "localhost")
PORT     = int(os.environ.get("INFLUXDB_PORT", "8086"))
DATABASE = os.environ.get("INFLUXDB_DATABASE", "homeassistant")
USERNAME = os.environ.get("INFLUXDB_USERNAME") or None
PASSWORD = os.environ.get("INFLUXDB_PASSWORD") or None

# ── MCP server ────────────────────────────────────────────────────────────────
server = Server("influxdb-1x-mcp")


def get_client() -> InfluxDBClient:
    return InfluxDBClient(
        host=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
        database=DATABASE,
    )


def result_to_dict(rs) -> list[dict]:
    """Convert ResultSet to a plain list of dicts."""
    rows = []
    for point in rs.get_points():
        rows.append(dict(point))
    return rows


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="influx_query",
            description=(
                "Execute a read-only InfluxQL query against the InfluxDB 1.x database. "
                "Returns results as JSON. Use for SELECT, SHOW MEASUREMENTS, SHOW FIELD KEYS, "
                "SHOW TAG VALUES, etc. "
                f"Default database: {DATABASE}. "
                "Example: SELECT mean(\"value\") FROM \"°C\" WHERE \"entity_id\" = 'sensor_name' "
                "AND time > now() - 24h GROUP BY time(5m)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "InfluxQL query to execute (SELECT or SHOW only)",
                    },
                    "database": {
                        "type": "string",
                        "description": f"Database name (default: {DATABASE})",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="influx_show_measurements",
            description="List all measurements (entity types) in the database, optionally filtered by regex.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Optional regex filter, e.g. 'kotel' to find boiler-related measurements",
                    }
                },
            },
        ),
        types.Tool(
            name="influx_show_tag_values",
            description=(
                "Show all tag values for a given measurement and tag key. "
                "For Home Assistant data use measurement='°C' and key='entity_id' "
                "to list all temperature sensors stored in InfluxDB."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "measurement": {
                        "type": "string",
                        "description": "Measurement name, e.g. '°C', 'W', '%', 'bar'",
                    },
                    "key": {
                        "type": "string",
                        "description": "Tag key to list values for (default: entity_id)",
                        "default": "entity_id",
                    },
                },
                "required": ["measurement"],
            },
        ),
        types.Tool(
            name="influx_ping",
            description="Test connection to InfluxDB and return server version.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:

    def ok(data: Any) -> list[types.TextContent]:
        return [types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False, default=str))]

    def err(msg: str) -> list[types.TextContent]:
        return [types.TextContent(type="text", text=json.dumps({"error": msg}, ensure_ascii=False))]

    client = get_client()

    try:
        if name == "influx_ping":
            version = client.ping()
            return ok({"status": "ok", "influxdb_version": version, "host": HOST, "port": PORT, "database": DATABASE})

        elif name == "influx_show_measurements":
            filt = arguments.get("filter", "")
            if filt:
                q = f"SHOW MEASUREMENTS WITH MEASUREMENT =~ /{filt}/"
            else:
                q = "SHOW MEASUREMENTS"
            rs = client.query(q)
            measurements = [m["name"] for m in rs.get_points()]
            return ok({"measurements": measurements, "count": len(measurements)})

        elif name == "influx_show_tag_values":
            measurement = arguments["measurement"]
            key = arguments.get("key", "entity_id")
            q = f'SHOW TAG VALUES FROM "{measurement}" WITH KEY = "{key}"'
            rs = client.query(q)
            values = [r["value"] for r in rs.get_points()]
            return ok({"measurement": measurement, "key": key, "values": values, "count": len(values)})

        elif name == "influx_query":
            query = arguments["query"].strip()
            # Safety: only allow read operations
            first_word = query.split()[0].upper() if query else ""
            if first_word not in ("SELECT", "SHOW"):
                return err("Only SELECT and SHOW queries are allowed (read-only server).")
            db = arguments.get("database", DATABASE)
            rs = client.query(query, database=db)
            rows = result_to_dict(rs)
            return ok({"database": db, "query": query, "rows": rows, "count": len(rows)})

        else:
            return err(f"Unknown tool: {name}")

    except (InfluxDBClientError, InfluxDBServerError) as e:
        return err(f"InfluxDB error: {e}")
    except Exception as e:
        return err(f"Unexpected error: {type(e).__name__}: {e}")
    finally:
        client.close()


def main():
    import asyncio
    print(f"InfluxDB 1.x MCP server starting — {HOST}:{PORT}/{DATABASE}", file=sys.stderr)
    asyncio.run(mcp.server.stdio.run_server(server))


if __name__ == "__main__":
    main()
