# Astronomical Data - Docker Deployment

Containerized astronomical data service (sun/moon/tides) for MidnightRider.

## Quick Start

### Option 1: In Main docker-compose.yml (Recommended)

Already integrated! Just run:

```bash
cd /home/aneto/docker/signalk
docker compose up -d astronomical
```

### Option 2: Standalone Services

For testing or separate deployment:

```bash
cd /home/aneto/docker/signalk/astronomical

# Build images
docker compose build

# Start services
docker compose up -d

# View logs
docker compose logs -f astronomical-init
docker compose logs -f astronomical-cron
```

## Services

### astronomical-init

**Type:** One-shot container (Type=oneshot equivalent)

- Runs once at startup
- Waits for InfluxDB (max 30s)
- Checks if data exists in InfluxDB
- If **NO data**: executes astronomical-data.sh (populates immediately)
- If **data exists**: exits silently
- Restart policy: `no` (doesn't restart after completion)

**Use case:** First deployment, ensuring data is available immediately

```bash
docker compose run --rm astronomical-init
# or
docker container run --rm --network host astronomical:latest
```

### astronomical-cron

**Type:** Long-running daemon

- Runs continuously
- Alpine cron daemon (dcron)
- Scheduled: **0 0 * * * (midnight daily)**
- Updates sun/moon/tides every 24 hours
- Restart policy: `unless-stopped`

**Use case:** Daily updates after initial deployment

```bash
docker compose up -d astronomical-cron
docker compose logs -f astronomical-cron
```

## Architecture

```
Startup
  ├─ astronomical-init (oneshot)
  │  ├─ Wait InfluxDB
  │  ├─ Check data exists?
  │  ├─ NO  → populate now
  │  └─ YES → skip (wait for cron)
  │
  └─ astronomical-cron (daemon, runs always)
     └─ Daily 00:00 → update data
```

## Configuration

Edit environment variables in docker-compose.yml:

```yaml
environment:
  - LAT=41.0534              # Latitude (Stamford Harbor, CT)
  - LON=-73.5387             # Longitude
  - NOAA_STATION=8467150     # NOAA tides station ID
  - INFLUX_URL=http://localhost:8086
  - INFLUX_TOKEN=...         # InfluxDB token
  - INFLUX_ORG=MidnightRider
  - INFLUX_BUCKET=signalk
```

## Integration with Main docker-compose.yml

The `astronomical` service is already added to the main `/home/aneto/docker/signalk/docker-compose.yml`:

```yaml
astronomical:
  build:
    context: .
    dockerfile: astronomical/Dockerfile
  container_name: astronomical
  restart: unless-stopped
  network_mode: host
  environment:
    - LAT=41.0534
    - LON=-73.5387
    - NOAA_STATION=8467150
    - INFLUX_URL=http://localhost:8086
    - INFLUX_TOKEN=4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==
    - INFLUX_ORG=MidnightRider
    - INFLUX_BUCKET=signalk
  depends_on:
    - influxdb
```

Start with main compose:

```bash
cd /home/aneto/docker/signalk
docker compose up -d astronomical
```

## Logs

### From main docker-compose.yml

```bash
docker logs astronomical -f
```

### From standalone docker-compose.yml

```bash
cd /home/aneto/docker/signalk/astronomical
docker compose logs -f astronomical-init
docker compose logs -f astronomical-cron
```

### Log file inside container

```bash
docker exec astronomical tail -f /tmp/astronomical-data.log
# or
docker exec astronomical-cron tail -f /tmp/astronomical-data.log
```

## Troubleshooting

### InfluxDB connection error

Check InfluxDB is running:
```bash
curl http://localhost:8086/health
```

### No data after container runs

Check logs:
```bash
docker logs astronomical
```

If error about `suncalc` module: npm dependencies weren't installed. Rebuild:
```bash
docker compose build --no-cache astronomical
```

### Cron not running

Check if cron process is alive:
```bash
docker exec astronomical-cron pgrep -a crond
```

### Manual execution (testing)

```bash
# Init container
docker run --rm --network host astronomical /app/init-astronomical-data.sh

# Cron container
docker run --rm --network host astronomical-cron /app/astronomical-data.sh
```

## Data Verification

After container runs, verify data in InfluxDB:

```bash
export INFLUX_TOKEN="4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA=="
export INFLUX_ORG="MidnightRider"

influx query 'from(bucket:"signalk") 
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement =~ /environment\.sun|environment\.moon|environment\.tide/)'
```

## Maintenance

### Update coordinates

Edit `docker-compose.yml`:
```yaml
environment:
  - LAT=41.0534
  - LON=-73.5387
```

Then redeploy:
```bash
docker compose up -d --build astronomical
```

### Update NOAA station

Find station: https://tides.noaa.gov/stations.html

Edit `docker-compose.yml`:
```yaml
environment:
  - NOAA_STATION=8467150
```

### View cron schedule

```bash
docker exec astronomical-cron cat /etc/crontabs/root
```

## Architecture Files

```
astronomical/
├── Dockerfile              # Init (oneshot)
├── Dockerfile.cron         # Cron (daily updates)
├── docker-compose.yml      # Standalone services
├── .dockerignore           # Docker build exclusions
└── DOCKER-README.md        # This file
```

## Notes

- **network_mode: host** → Direct access to localhost:8086 (InfluxDB)
- **restart: unless-stopped** → Survives system reboots
- **No volumes needed** → Stateless service (data → InfluxDB)
- **Lightweight** → Alpine + minimal dependencies
- **Offline capable** → suncalc works without internet (NOAA requires internet)

## Author

Aneto (MidnightRider J/30)
2026-04-20
