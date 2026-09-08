# InfluxDB Docker-Internal Authentication Integration

## Overview

This document describes the Docker-internal InfluxDB authentication provider system, which securely retrieves InfluxDB tokens without exposing them on the host command line.

**Status:** Production Ready  
**Version:** 1.0  
**Last Updated:** 2026-09-08

---

## Features

### 1. Docker-Internal CLI Authentication (Primary)

- **Method:** `docker exec` + `influx auth list`
- **Security:** Token retrieved inside container; never exposed on host CLI
- **Availability:** Requires Docker, running InfluxDB container, and compose file
- **Fallback:** If Docker unavailable, tries token file or environment

### 2. Secure Token File (Fallback)

- **Method:** Read from file with restricted permissions
- **Security:** File should be mode `0600` or similar
- **Availability:** Requires readable token file
- **Locations searched:**
  - `.influxdb-token`
  - `~/.influxdb-token`
  - `/home/pi/.influxdb-token`
  - `/etc/influxdb/.influxdb-token`

### 3. Environment Variable (Fallback)

- **Method:** Read from `INFLUXDB_TOKEN` env var
- **Security:** Less secure; credentials in environment
- **Availability:** Requires env var set
- **Alternative:** Use custom env var with `--env-var` flag

---

## Architecture

### Authentication Chain

```
┌─────────────────────────────────┐
│ AuthProviderChain               │
│ (Try each in order)             │
└─────────────────────────────────┘
    ↓
    1. DockerInternalCliAuthProvider
    │  - Checks: Docker, compose file, container running
    │  - Success: Return token from docker exec
    │  - Fail: Try next provider
    ↓
    2. SecureTokenFileAuthProvider
    │  - Checks: File exists, readable
    │  - Success: Return token from file
    │  - Fail: Try next provider
    ↓
    3. EnvironmentTokenAuthProvider
    │  - Checks: Env var set and not empty
    │  - Success: Return token from env
    │  - Fail: Return error
```

### Component Overview

| Component | Role | Location |
|-----------|------|----------|
| `AuthProvider` (ABC) | Base class for all providers | `src/auth_providers.py` |
| `DockerInternalCliAuthProvider` | Docker exec-based auth | `src/auth_providers.py` |
| `SecureTokenFileAuthProvider` | File-based auth | `src/auth_providers.py` |
| `EnvironmentTokenAuthProvider` | Environment var auth | `src/auth_providers.py` |
| `AuthProviderChain` | Fallback chain manager | `src/auth_providers.py` |
| `Transport` (ABC) | Client-server transport | `src/influx_client.py` |
| `InfluxDBCLITransport` | CLI-based transport | `src/influx_client.py` |
| `InfluxDBClient` | High-level API | `src/influx_client.py` |

---

## Usage

### Python API

#### Basic Query

```python
from src.influx_client import InfluxDBClient

client = InfluxDBClient(
    url="http://localhost:8086",
    org="midnight-rider",
)

# Query returns CSV string
result = client.query(
    flux_query='from(bucket:"midnight_rider") |> range(start:-1h)',
)
print(result)
```

#### Streaming Query to File

```python
# Stream results to file (more memory-efficient)
bytes_written = client.stream_query(
    flux_query='from(bucket:"midnight_rider") |> range(start:-7d)',
    org="midnight-rider",
    output_file="results.csv",
    progress_callback=lambda b: print(f"Progress: {b} bytes"),
)
print(f"Wrote {bytes_written} bytes")
```

#### Custom Auth Provider

```python
from src.auth_providers import SecureTokenFileAuthProvider

token_provider = SecureTokenFileAuthProvider(
    token_file="/etc/influxdb/.token"
)

client = InfluxDBClient(
    url="http://localhost:8086",
    auth_provider=token_provider,
)

result = client.query(flux_query='...', org="midnight-rider")
```

#### Docker-Specific Auth

```python
from src.auth_providers import DockerInternalCliAuthProvider

docker_auth = DockerInternalCliAuthProvider(
    compose_file="docker-compose.yml",
    docker_service="influxdb",
)

client = InfluxDBClient(auth_provider=docker_auth)
result = client.query(flux_query='...', org="midnight-rider")
```

### Command-Line Interface

#### Basic Query

```bash
cd /home/pi/midnightrider-navigation

# Automatic auth (try Docker → Token File → Environment)
python3 -m src.cli query 'from(bucket:"midnight_rider") |> range(start:-1h)'

# Stream to file
python3 -m src.cli --output results.csv query 'from(bucket:"midnight_rider") |> range(start:-7d)'
```

#### Docker-Specific Auth

```bash
# Explicit Docker-internal method
python3 -m src.cli \
  --auth-method docker-internal-cli \
  --compose-file docker-compose.yml \
  --docker-service influxdb \
  query 'from(bucket:"midnight_rider") |> range(start:-1h)'
```

#### Token File Auth

```bash
# Use specific token file
python3 -m src.cli \
  --auth-method token-file \
  --token-file ~/.influxdb-token \
  query 'from(bucket:"midnight_rider")'
```

#### Environment Variable Auth

```bash
# Use environment variable
export INFLUXDB_TOKEN="my-token-here"

python3 -m src.cli \
  --auth-method environment \
  query 'from(bucket:"midnight_rider")'

# Or custom env var
export MY_INFLUX_TOKEN="token-here"

python3 -m src.cli \
  --auth-method environment \
  --env-var MY_INFLUX_TOKEN \
  query 'from(bucket:"midnight_rider")'
```

#### Health Check

```bash
python3 -m src.cli health
# Output: ✓ InfluxDB is healthy
```

#### Dry Run

```bash
python3 -m src.cli --dry-run query 'from(bucket:"midnight_rider")'
# Shows command without executing
```

#### Load Query from File

```bash
# my_query.flux
from(bucket:"midnight_rider")
  |> range(start:-7d)
  |> filter(fn: (r) => r._measurement == "wind")

# Run it
python3 -m src.cli --query-file my_query.flux query
```

---

## Security Considerations

### Token Exposure Prevention

#### ✅ Safe: Docker Method

```bash
# Token is INSIDE container, never on host command line
docker exec influxdb influx auth list --format json
```

Verification:
```bash
ps aux | grep influx
# Token NOT visible in process list
```

#### ⚠️ Less Safe: File Method

Token is on disk. Protect with file permissions:
```bash
ls -l ~/.influxdb-token
# -rw------- 1 user user 64 Sep  8 12:34 ~/.influxdb-token
```

Ensure:
- Owner is the running user
- Permissions are `0600` (read/write owner only)
- File is on encrypted filesystem

#### ⚠️ Least Safe: Environment Variable

Token is in memory and process environment:
```bash
ps aux | grep INFLUXDB_TOKEN
# ⚠️ Token IS visible to ps/env/cat /proc/*/environ
```

Only use for:
- Development/testing
- CI/CD with short-lived tokens
- When host is already compromised

### Docker Compose Security

Protect `docker-compose.yml`:
```bash
chmod 600 docker-compose.yml
```

Don't commit credentials to the file:
```yaml
# ✅ Good: Read token at runtime
environment:
  - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}

# ❌ Bad: Hardcoded credentials
environment:
  - INFLUXDB_TOKEN=my-secret-token-here
```

---

## Logging & Audit

### Audit Trail

All authentication events are logged:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

client = InfluxDBClient()
token = client.auth_provider.get_token()
# Output:
# DEBUG:auth_providers:DockerInternalCliAuthProvider not available: ...
# DEBUG:auth_providers:SecureTokenFileAuthProvider not available: ...
# DEBUG:auth_providers:Successfully retrieved token from $INFLUXDB_TOKEN
# INFO:auth_providers:Authentication successful via: environment
```

### Sanitized Logging

Logs are sanitized:
- ❌ Token value is NEVER logged
- ✅ Method name is logged
- ✅ Availability checks logged
- ✅ Fallback chain logged

---

## Error Handling

### Query Errors

```python
try:
    result = client.query(
        flux_query='from(bucket:"nonexistent")',
        org="midnight-rider",
    )
except RuntimeError as e:
    print(f"Query failed: {e}")
    # Output: Query failed: bucket not found
```

### Authentication Errors

```python
# All auth methods fail
try:
    result = client.query(...)
except RuntimeError as e:
    print(f"Auth failed: {e}")
    # Output: Auth failed: All authentication providers exhausted
```

### Streaming Errors

```python
# Stream interrupted
try:
    bytes_written = client.stream_query(
        flux_query='from(bucket:"midnight_rider")',
        org="midnight-rider",
        output_file="/full/disk.csv",
    )
except RuntimeError as e:
    print(f"Stream failed: {e}")
    # Output: Stream failed: No space left on device
```

---

## Testing

### Run All Tests

```bash
cd /home/aneto/.openclaw/workspace
python -m pytest tests/ -v
```

### Test Coverage

| Area | Tests | Status |
|------|-------|--------|
| Docker Provider | 11 | ✅ Pass |
| Token File Provider | 8 | ✅ Pass |
| Environment Provider | 9 | ✅ Pass |
| Auth Chain | 6 | ✅ Pass |
| Integration | 2 | ✅ Pass |
| Influx Client | 23 | ✅ Pass |
| Streaming | 3 | ✅ Pass |
| **Total** | **62** | **✅ Pass** |

### Test Examples

#### Docker Provider Tests

```python
def test_get_token_success():
    """Verify token retrieval via docker exec"""

def test_token_not_in_command_line():
    """Verify token never appears in ps output"""

def test_get_token_caching():
    """Verify token is cached after first retrieval"""
```

#### Streaming Tests

```python
def test_stream_multiple_tables():
    """Handle multiple Flux result tables"""

def test_stream_large_result():
    """Stream large results with progress tracking"""

def test_stream_query_timeout():
    """Handle timeout during streaming"""
```

---

## Deployment

### Docker Compose Setup

```yaml
version: '3.8'
services:
  influxdb:
    image: influxdb:2-alpine
    ports:
      - "8086:8086"
    environment:
      INFLUXDB_DB: midnight_rider
      INFLUXDB_ADMIN_USER: admin
      INFLUXDB_ADMIN_PASSWORD: ${INFLUXDB_PASSWORD}
    volumes:
      - influxdb-data:/var/lib/influxdb2
    healthcheck:
      test: ["CMD", "influx", "health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

### Systemd Service (Portal Integration)

```ini
[Unit]
Description=InfluxDB Query Service
After=docker.service
Wants=docker.service

[Service]
Type=simple
WorkingDirectory=/home/pi/midnightrider-navigation
ExecStart=/usr/bin/python3 -m src.cli query \
  'from(bucket:"midnight_rider") |> range(start:-1h)'
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

---

## Troubleshooting

### Docker Method Not Working

```bash
# Check 1: Docker compose file exists
test -f docker-compose.yml && echo "✓ compose file" || echo "✗ compose file missing"

# Check 2: Container is running
docker compose ps influxdb
# Should show container status "running"

# Check 3: InfluxDB CLI is available
docker compose exec influxdb influx --version

# Check 4: Auth works
docker compose exec influxdb influx auth list --format json
```

### Token File Not Working

```bash
# Check 1: File exists
test -f ~/.influxdb-token && echo "✓ file exists" || echo "✗ file missing"

# Check 2: File is readable
test -r ~/.influxdb-token && echo "✓ readable" || echo "✗ not readable"

# Check 3: File has content
wc -c ~/.influxdb-token
# Should show non-zero byte count

# Check 4: Token is valid
TOKEN=$(cat ~/.influxdb-token)
influx auth list --token "$TOKEN"
```

### Environment Variable Not Working

```bash
# Check 1: Env var is set
echo $INFLUXDB_TOKEN
# Should print token (or nothing if not set)

# Check 2: Env var is not empty
test -n "$INFLUXDB_TOKEN" && echo "✓ set" || echo "✗ not set"

# Check 3: Token is valid
influx auth list --token "$INFLUXDB_TOKEN"
```

---

## Roadmap

### Version 1.1 (Q4 2026)

- [ ] Support for InfluxDB Cloud token refresh
- [ ] Automatic token rotation via Docker secrets
- [ ] Audit log export to syslog

### Version 2.0 (2027)

- [ ] Vault integration (HashiCorp Vault)
- [ ] SSO support (LDAP, OAuth2)
- [ ] Hardware token support (FIDO2/YubiKey)

---

## References

- [InfluxDB CLI Docs](https://docs.influxdata.com/influxdb/latest/reference/cli/)
- [Docker CLI Reference](https://docs.docker.com/reference/cli/docker/)
- [OWASP: Secrets Management](https://owasp.org/www-community/controls/Secrets_Management)
- [CWE-798: Hardcoded Credentials](https://cwe.mitre.org/data/definitions/798.html)

---

**Built for Midnight Rider Navigation System**  
**Deploy Date:** May 22, 2026
