# 🔄 RECOVERY GUIDE — Bringing Midnight Rider Back Up

**Purpose:** what to do, in order, when the boat's systems are down or a
Raspberry Pi has to be rebuilt from nothing.

**Rewritten:** 2026-09-18 (chantier H12) — **Version 2.0**

> **Why this document was rewritten.** Version 1.1 dated from 2026-04-19 and
> described a layout that no longer exists. An audit on 2026-09-18 found that
> of the 53 file paths it cited, **2 existed**. It named seven MCP servers by
> filenames (`racing-server.js`) that were never in this repository, told the
> reader to query a bucket named `signalk` that does not exist, listed three
> cron jobs pointing at scripts that were never written — and, most seriously,
> STEP 1 instructed the reader to bring Signal K up with `docker-compose up -d`,
> which is the one action the architecture forbids. That instruction is the
> most plausible origin of the orphaned `signalk` Docker container found
> `Exited (137)` after four months.
>
> Two sections were removed rather than corrected, because they duplicated
> information that is already correct elsewhere: the Claude configuration
> template now lives only in `mcp/claude_desktop_config.example.json`, and the
> file-structure map only in `docs/INDEX.md`. A recovery guide that duplicates
> other documents goes stale faster than the system it is meant to rescue.

---

## 0. WHAT THIS DOCUMENT OWNS

This guide owns **procedure**: the order of operations, and how to tell
whether each step worked. It owns nothing else.

| You need | Read |
|---|---|
| System overview, ports, services | `docs/ARCHITECTURE-MASTER.md` |
| Field quick-reference on race day | `SYSTEM-SUMMARY.md` |
| Where any document lives | `docs/INDEX.md` |
| Claude / MCP client configuration | `mcp/claude_desktop_config.example.json` |
| InfluxDB setup and cloud replication | `docs/setup/INFLUXDB-CONFIG.md` |
| Signal K plugin inventory and status | `docs/SIGNALK-PLUGINS-INVENTORY.md` |
| N2K bus and PGN flow | `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md` |
| Grafana dashboards | `docs/DASHBOARDS-README.md` |

**Host:** `midnightrider.local` — always use the mDNS alias. The Pi takes its
address from DHCP; any hard-coded address in a procedure is a procedure that
will fail on the day you need it.

---

## 1. START ORDER

### ⛔ The one rule that overrides everything

**Signal K runs under `systemctl`. Never under Docker. Never
`docker-compose up` for Signal K.**

There is no `docker/` directory in this repository and no Signal K image.
A container named `signalk` on this Pi is a leftover, not a service — it
should be removed, not started.

### 1.1 — Signal K (port 3000)

```bash
sudo systemctl start signalk
systemctl status signalk --no-pager
```

Unit file: `etc/systemd/system/signalk.service`
Working directory: `/home/aneto/.signalk` (outside this repository)
Binary: `/usr/bin/signalk-server`

Expected: `active (running)`, `Restart=always`, low `NRestarts`.

### 1.2 — Docker services

Four containers, and only four, are defined in `docker-compose.yml` at the
repository root:

| Container | Port | Role |
|---|---|---|
| `influxdb` | 8086 | time-series store, InfluxDB 2.8 |
| `grafana` | 3001 | dashboards |
| `regatta` | 5000 | regatta server |
| `start-line-worker` | — | start-line computation worker |

```bash
cd ~/midnightrider-navigation
docker compose up -d
docker ps --format '{{.Names}}\t{{.Status}}'
```

Expected: those four `Up`. Anything else listed is a leftover.

### 1.3 — Scheduled tasks

**There is no crontab on this system.** Scheduling is done with systemd
timers. See § 4.

---

## 2. VERIFY EACH LINK IN THE CHAIN

Work down the chain in order. The first link that fails is the one to fix;
everything below it will look broken whether it is or not.

```bash
bash scripts/check-system.sh
```

That script covers most of the following. Run the individual checks when it
reports a problem and you need to know which link.

### 2.1 — Sensors reach the Pi

```bash
ls -l /dev/serial/by-id/ 2>/dev/null
ip -brief link | grep -i can
```

Empty output on both means no instrument is connected. **That is the normal
state when the boat is at the dock with the panel off** — it is not a fault.
See `logs/debug/ingestion-au-repos-2026-09-18.md` for what a correctly idle
chain looks like.

### 2.2 — Signal K holds a vessel

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self | head -c 400
```

A `404` with `{}` on `/vessels` means Signal K is up but has received nothing.
Go back to 2.1 before touching anything downstream.

### 2.3 — InfluxDB answers

```bash
curl -s http://localhost:8086/health
```

Expected: `"status":"pass"`, `ready for queries and writes`.

### 2.4 — The token is accepted

The token is **never written in this repository**. It lives in `.env`, which
`.gitignore` excludes. Read it into the environment, never into a document:

```bash
set -a; . ./.env; set +a
curl -s -H "Authorization: Token $INFLUXDB_TOKEN" \
  http://localhost:8086/api/v2/buckets | head -c 300
```

To rotate it: `scripts/rotate-token.sh`.

### 2.5 — The bucket exists and holds data

There is **one** bucket: `midnight_rider`, organisation `MidnightRider`,
retention unlimited (measured 2026-09-18). No bucket named `signalk` has ever
existed on this server.

```bash
influx query --org MidnightRider --token "$INFLUXDB_TOKEN" '
from(bucket:"midnight_rider")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "navigation.position")
  |> last()'
```

An empty result over 30 days means nothing has been written for a month.
A result whose timestamp is old tells you exactly when ingestion stopped,
which is usually the most useful single fact in a recovery.

### 2.6 — Signal K is writing to InfluxDB

The `signalk-to-influxdb2` plugin carries this link. Its configuration lives
in `/home/aneto/.signalk/plugin-config-data/` (outside this repository) and
must name organisation `MidnightRider` and bucket `midnight_rider`.

---

## 3. RESTORE THE MCP SERVERS

**11 servers, 48 tools**, all under `mcp/servers/`:

| Server | Tools | Server | Tools |
|---|---|---|---|
| `astronomical.js` | 4 | `polar.js` | 5 |
| `buoy.js` | 5 | `race.js` | 7 |
| `competitor.js` | 5 | `racing.js` | 2 |
| `crew.js` | 3 | `system.js` | 5 |
| `electrical.js` | 5 | `weather.js` | 3 |
| `imu.js` | 4 | | |

`racing.js` exposes exactly two tools — `get_historical_snapshot` and
`get_snapshot` — two thin doors onto one collection engine. Two is correct;
if you find more, someone has reintroduced a second query path.

```bash
cd ~/midnightrider-navigation
git pull origin main
ls mcp/servers/*.js | wc -l        # expect 11
bash scripts/sync-plugins.sh       # deploy to the OpenClaw workspace
```

Deployed copies live in `/home/aneto/.openclaw/workspace/mcp/`, which is where
the client configuration points. The repository holds the source; the workspace
holds what runs.

Client configuration: copy from `mcp/claude_desktop_config.example.json`. It is
the single source of truth for server names, paths and environment, and it is
kept correct. Do not retype it from memory.

---

## 4. RESTORE SCHEDULED TASKS

Four systemd timers, defined under `etc/systemd/system/`:

Measured on the Pi on 2026-09-20. **One timer is installed and running, not four.**

| Timer | Installed | State | What it does |
|---|---|---|---|
| `midnight-logs-commit.timer` | yes | `enabled`, `active`, every 15 min | commits logs to git |
| `mediaman.timer` | **no** | `LoadState=not-found` | MediaMan article pipeline — defect 90 |
| `mediaman-events.timer` | **no** | `LoadState=not-found` | MediaMan event pipeline — defect 90 |
| `midnight-logsync.timer` | yes | `disabled`, **deliberately** | see the warning below |

> ⛔ **Never enable `midnight-logsync.timer`.**
> Its `ExecStart` truncates in place any service log over 900 kB down to its
> last 300 lines, with no backup. It declares no `User=`, so it would run as
> root in a repository owned by `aneto`. Its `WorkingDirectory=/home/pi/...`
> has never existed on this boat. H7e disarmed it on 2026-09-17 and wrote the
> reason in capitals at the top of the unit file itself. Earlier versions of
> this very guide told you to enable it — that was defect 89.

```bash
# Deploy the reference units, EXCEPT the disarmed one.
for unite in etc/systemd/system/*.service etc/systemd/system/*.timer; do
  case "$unite" in *midnight-logsync*) continue ;; esac
  sudo cp "$unite" /etc/systemd/system/
done
sudo systemctl daemon-reload
sudo systemctl enable --now midnight-logs-commit.timer
systemctl list-timers --all | grep -E 'mediaman|midnight'
systemctl list-units --state=failed
```

As of 2026-09-20, `systemctl list-units --state=failed` prints
`telegraf.service`, and nothing else. Telegraf's configuration asks for a
parser named `nmea`, which Telegraf does not provide; the service has
therefore never started a single time (defect 71). `midnight-logsync.service`
no longer appears there: it is disabled, not failing. Four installed units
diverge from their reference copy in this repository (defect 91). Background
on the timers: `logs/debug/timers-systemd-2026-09-17.md`.

---

## 5. RUN THE TESTS

```bash
cd ~/midnightrider-navigation
python3 -m pytest tests/mcp        # expect 104 passed
python3 -m pytest tests/mediaman   # expect 495 passed
```

`npm test` in `mcp/` runs those same two suites; there is nothing else to
run. A separate JavaScript harness lived in `tests/mcp/js/` until 2026-09-18.
It addressed seven servers by filenames that never existed and hard-coded a
bucket that never existed, and `mcp/package.json` pointed at it through a
path that was also wrong, so `npm test` had been failing on contact for
months. It was deleted rather than repaired: nothing anywhere depended on a
passing result from it.

Python dependencies, if the environment is new:

```bash
pip3 install -r ble/requirements.txt       # bleak, for the BLE daemons
pip3 install -r scripts/requirements.txt   # pyserial, for enable_gnhpr.py
```

There is no `requirements.txt` at the repository root, by design.

---

## 6. DISASTER RECOVERY SCENARIOS

### Scenario 1 — MCP servers deleted or corrupted

```bash
cd ~/midnightrider-navigation && git pull origin main
ls mcp/servers/*.js | wc -l    # 11
bash scripts/sync-plugins.sh
python3 -m pytest tests/mcp
```

Recovery time: under 5 minutes. Nothing is lost; the repository is the source.

### Scenario 2 — No data in InfluxDB

Establish **whether the boat sailed** before treating this as a fault. An idle
chain and a broken chain look identical from a query. Work § 2 downward.

If the boat did sail and the data is missing, the external collectors can be
replayed by hand — they fetch from public APIs and do not depend on the boat:

```bash
bash scripts/weather-logger.sh       # Open-Meteo
python3 scripts/noaa_collector.py    # NOAA buoys, Long Island Sound
```

Instrument data cannot be replayed. It is only in InfluxDB, and in the Google
Drive backups produced by `scripts/influxdb-gdrive-backup.sh`.

### Scenario 3 — Scheduled tasks lost

Re-apply § 4. Recovery time: under 2 minutes.

### Scenario 4 — MCP client configuration lost

Copy `mcp/claude_desktop_config.example.json` to the client's configuration
path and restart the client. Recovery time: under 1 minute.

### Scenario 5 — Complete loss, new Raspberry Pi

```bash
git clone https://github.com/Aneto152/midnightrider-navigation.git
cd midnightrider-navigation
bash scripts/install-midnight-rider.sh
```

Then, in order: § 1 (start), § 4 (timers), § 3 (MCP), § 5 (tests), § 2 (verify).

Two things are **not** in the repository and must be restored by hand:
`.env` (InfluxDB token — generate a new one, do not attempt to recover the old)
and `/home/aneto/.signalk/` (Signal K's own configuration and plugin settings).

Dashboards are redeployed with `scripts/deploy-dashboards-to-grafana.sh`.

---

## 7. POST-RECOVERY CHECKLIST

- [ ] `systemctl status signalk` → `active (running)`
- [ ] `docker ps` → exactly `influxdb`, `grafana`, `regatta`, `start-line-worker`
- [ ] No container named `signalk` — if one exists, remove it
- [ ] `curl localhost:8086/health` → `pass`
- [ ] Bucket `midnight_rider` present, organisation `MidnightRider`
- [ ] `ls mcp/servers/*.js | wc -l` → `11`
- [ ] `python3 -m pytest tests/mcp` → 104 passed
- [ ] `python3 -m pytest tests/mediaman` → 495 passed
- [ ] `systemctl list-units --state=failed` → empty
- [ ] `systemctl list-timers` → `midnight-logs-commit.timer` scheduled, the only one installed (defect 90)
- [ ] With the boat powered: a fresh point in `navigation.position` within 5 minutes
- [ ] `git status` → clean

---

## 8. WHAT THIS GUIDE DOES NOT COVER

- **Instrument-level faults.** A sensor that reports nothing is a hardware
  question: see the datasheet in `docs/HARDWARE/` for that instrument.
- **The N2K bus.** See `docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`.
- **Secrets.** No token, password or key appears anywhere in this repository,
  and none should ever be added to it. `scripts/check-staged-secrets.py` runs
  before every commit to enforce that.
- **Guarantees.** This guide has been checked against the repository on
  2026-09-18: every path it cites exists, and a test in
  `tests/mcp/test_h9b_coherence_doc_code.py` fails if that stops being true.
  It has **not** been rehearsed end to end on real hardware. Restoring a Pi
  from nothing by following § 6 Scenario 5 is still an untested procedure,
  and the honest thing is to say so rather than to promise 45 minutes.

---

**Audited and rewritten:** 2026-09-18, chantier H12
**Supersedes:** version 1.1 of 2026-04-27, which cited 53 paths of which 2 existed
