# Astronomical MCP Server

Model Context Protocol (MCP) server for accessing sun/moon/tide data from InfluxDB.

## Overview

Provides a standardized MCP interface for querying astronomical data:
- **Sun times** (sunrise, sunset)
- **Moon data** (rise/set, phase, illumination)
- **Tide predictions** (high/low times and levels)
- **Next events** (upcoming astronomical events)

## Installation

```bash
cd /home/aneto/docker/signalk/mcp
npm install
chmod +x astronomical-server.js test-mcp.js
```

## Usage

### Start the MCP Server

```bash
./astronomical-server.js
```

Server listens on **stdin/stdout** (stdio transport).

### Configure in Claude/Cursor/IDE

**claude_desktop_config.json** (Cursor/Claude Desktop):

```json
{
  "mcpServers": {
    "astronomical": {
      "command": "/home/aneto/docker/signalk/mcp/astronomical-server.js",
      "env": {
        "INFLUX_URL": "http://localhost:8086",
        "INFLUX_TOKEN": "your-token-here",
        "INFLUX_ORG": "MidnightRider",
        "INFLUX_BUCKET": "signalk"
      }
    }
  }
}
```

**With global npm install:**

```bash
npm install -g @aneto/astronomical-mcp-server
```

Then in config:

```json
{
  "mcpServers": {
    "astronomical": {
      "command": "astronomical-mcp-server"
    }
  }
}
```

## Tools

### get_sun_data

Get sunrise and sunset times for a specific date.

**Parameters:**
- `date` (string, optional): Date in YYYY-MM-DD format (default: today)

**Response:**
```json
{
  "date": "2026-04-20",
  "sunrise": "2026-04-19T10:10:06.563Z",
  "sunset": "2026-04-19T23:38:38.897Z",
  "source": "astronomical"
}
```

**Example:**
```
Claude: "What time is sunrise today?"
→ Tool: get_sun_data()
← Result: 10:10 AM
```

### get_moon_data

Get moon phase, illumination, rise/set times for a date.

**Parameters:**
- `date` (string, optional): Date in YYYY-MM-DD format (default: today)

**Response:**
```json
{
  "date": "2026-04-20",
  "moonrise": "2026-04-20T11:46:32.348Z",
  "moonset": "2026-04-20T02:54:46.723Z",
  "illumination": 0.0929,
  "phase": "new_moon",
  "source": "astronomical"
}
```

**Example:**
```
Claude: "What's the moon phase?"
→ Tool: get_moon_data()
← Result: new moon at 9.3% illumination
```

### get_tide_data

Get high/low tide times and levels for a date.

**Parameters:**
- `date` (string, optional): Date in YYYY-MM-DD format (default: today)

**Response:**
```json
{
  "date": "2026-04-20",
  "tideHighTime": "2026-04-20T14:30:00-04:00",
  "tideHighLevel": 2.15,
  "tideLowTime": "2026-04-20T20:45:00-04:00",
  "tideLowLevel": 0.45,
  "source": "astronomical"
}
```

**Example:**
```
Claude: "When's high tide?"
→ Tool: get_tide_data()
← Result: High tide at 2:30 PM (2.15m), low at 8:45 PM (0.45m)
```

### get_next_event

Get the next upcoming astronomical event.

**Parameters:** None

**Response:**
```json
{
  "time": "2026-04-19T23:38:38.897Z",
  "type": "sunset"
}
```

**Example:**
```
Claude: "What's the next astronomical event?"
→ Tool: get_next_event()
← Result: Sunset at 11:38 PM (in 1 hour)
```

## Testing

### Test Locally

```bash
./test-mcp.js
```

Sends sample requests and displays responses.

### Test with Cursor

1. Set up config (see above)
2. Restart Cursor/IDE
3. Ask Claude a question about sun/moon/tides

**Example prompts:**
- "What time is sunrise today?"
- "When's the next full moon?"
- "Show me next week's tides"
- "Tell me about today's astronomical events"

## MCP Protocol

This server implements MCP 2024-11-05 with:

**Methods:**
- `initialize` — Handshake and server info
- `tools/list` — Available tools
- `tools/call` — Execute a tool

**Transport:** stdio (stdin/stdout JSON-RPC)

**Example request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_sun_data",
    "arguments": {
      "date": "2026-04-20"
    }
  }
}
```

## Environment Variables

```bash
INFLUX_URL=http://localhost:8086          # InfluxDB host
INFLUX_TOKEN=your-token                   # InfluxDB auth token
INFLUX_ORG=MidnightRider                  # InfluxDB org
INFLUX_BUCKET=signalk                     # InfluxDB bucket
```

## Architecture

```
Claude/Cursor/IDE
     ↓
MCP Client (stdio)
     ↓
astronomical-server.js
     ↓
InfluxDB (HTTP)
     ↓
Astronomical Data (environment.sun/moon/tide.*)
```

## Limitations

- **InfluxDB connectivity required** — Must have working InfluxDB
- **Token required** — Valid token must be in environment
- **Daily data** — Astronomical data updated once per day
- **Flux syntax** — Uses InfluxDB Flux queries (not SQL)

## Use Cases

### Sailing Navigation

```
Claude: "I'm planning a race tomorrow. Show me sunset and moon phase."
→ get_sun_data + get_moon_data
← Sunset at 11:45 PM, moon 5% (new moon)
```

### Weather Planning

```
Claude: "What are high tides this week?"
→ get_tide_data (multiple days)
← High tides: Mon 2.15m, Tue 2.18m, Wed 2.12m, etc.
```

### Contextual Decisions

```
Claude: "Should I delay departure?"
→ get_next_event (check sunrise)
← Next sunrise in 6 hours at 10:10 AM
→ Recommendation: "Wait for sunrise for better visibility"
```

## Troubleshooting

### 401 Unauthorized

Token is invalid or expired. Update `INFLUX_TOKEN` environment variable.

```bash
export INFLUX_TOKEN="your-new-token"
./astronomical-server.js
```

### No Data Returned

Data hasn't been populated yet. Ensure `astronomical-data.sh` has run:

```bash
/home/aneto/docker/signalk/scripts/astronomical-data.sh
```

### Parse Errors

Check MCP client is sending valid JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "...",
  "params": {...}
}
```

## Author

Aneto (MidnightRider J/30)
2026-04-20

## License

MIT
