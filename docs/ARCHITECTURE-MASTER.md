# Midnight Rider Navigation System — Architecture Master Reference
Version: 5.2 (N2K SSOT architecture, 2026-06-15)
Last Updated: 2026-06-15
Status: ✅ PRODUCTION — Canonical architecture reference
Source: Merged from ARCHITECTURE-REFERENCE-2026-05-20.md

> Note: This document is now the single canonical architecture reference.
> All future updates MUST be made to this file only.

---

## 1. VUE D'ENSEMBLE

Midnight Rider embarque un système de navigation open-source basé sur un Raspberry Pi 4,
collectant les données de tous les instruments via trois réseaux physiques distincts
(NMEA 2000, Bluetooth LE, USB), les centralisant dans Signal K, les persistant dans
InfluxDB et les visualisant dans Grafana.

**Publication subsystem (offline only):**

An internal publication subsystem manages outbound race performance reporting with a
State-based architecture: `READY → VALIDATED → SENDING → SENT` for successful dry-run publication,
with operator-controlled recovery paths for ambiguous outcomes (`UNKNOWN → SENT_RECONCILED`,
`UNKNOWN → RETRY_AUTHORIZED → READY`, `UNKNOWN → DEAD_LETTER`).

- **PublicationBridge**: Offline adapter accepting injected PublicationStateStore and
  TelegramSender-compatible mock. Enforces dry-run-only publication without network calls.
- **PublicationReconciler**: Manual evidence-based reconciliation for UNKNOWN publication outcomes.
- **PublicationEvidenceRecord**: Immutable evidence with operator identity and source-authenticated
  reference format (e.g., `manual_ui:2026-08-31T15:00:00Z:ref-001`).
- **StagingActivation**: One-shot staging gate enforcing mode="staging" and dry_run=True only.
  No daemon, no systemd, no scheduler. Uses injected PublicationBridge for isolated validation.

No live Telegram publication has been implemented. No runtime activation has occurred.
No systemd units are enabled. No credentials are stored in code or logs.
Runtime E2E validation remains incomplete.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MIDNIGHT RIDER — STACK                       │
│                                                                 │
│  CAPTEURS ──► COLLECTE ──► TRAITEMENT ──► STOCKAGE ──► VISU   │
│                                                                 │
│  UM982 (USB)  ──────────────────────────► Signal K :3000       │
│  WIT IMU (BLE) ─────────────────────────► │                    │
│  Calypso UP10 (BLE/UDP) ────────────────► │ ──► InfluxDB :8086 │
│  WS320 (N2K/YDNU-02) ───────────────────► │         │          │
│  YDBC-05 (N2K/YDNU-02) ─────────────────► │         │          │
│  AIS700 (N2K/YDNU-02) ──────────────────► │         │          │
│                                           │         │          │
│  SOK BMS (BLE) ─────────────────────────────────────► InfluxDB │
│                                                      │          │
│                                           │         ▼          │
│  Signal K ──► sk-to-nmea2000 (npm v2.24.0) ────────────► Grafana :3001│
│                    │                                            │
│                    ▼                                            │
│               YDNU-02 (USB/N2K) ──► N2K backbone               │
│                                    ├── Vulcan 7 FS              │
│                                    ├── WS320 base               │
│                                    ├── YDBC-05                  │
│                                    └── AIS700                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. MATÉRIEL EMBARQUÉ

### 2.1 Serveur de navigation

| Composant | Détail |
|-----------|--------|
| **Raspberry Pi 4 Model B** | 4 Go RAM, microSD 64 Go |
| **Accès local** | `midnightrider.local` (mDNS/Avahi) — IP DHCP variable |
| **OS** | Raspberry Pi OS (Debian 12 Bookworm) |
| **Rôle** | Signal K server, Docker host (InfluxDB, Grafana), gateway BLE, scripts Python |
| **Alimentation** | 12V → 5V USB-C via convertisseur DC/DC |
| **Accès local** | SSH (`aneto@midnightrider.local`) |
| **Accès distant** | Cloudflare Tunnel (voir `CLOUDFLARE-TUNNEL-URL.md`) |

### 2.2 Instruments actifs

| # | Instrument | Modèle | Protocole | Rôle principal |
|---|------------|--------|-----------|---------------|
| 1 | GPS + Cap | Unicore UM982 | USB serial | Position, cap vrai, SOG, COG |
| 2 | IMU | WIT WT901BLECL | Bluetooth LE 5.0 | Gîte, assiette, accélération |
| 3 | Vent masthead | Calypso UP10 | Bluetooth LE | Vent apparent/vrai + temp air |
| 4 | Vent masthead (N2K) | B&G WS320 | NMEA 2000 | Vent apparent → Vulcan 7 direct |
| 5 | Passerelle N2K | Yacht Devices YDNU-02 | USB + NMEA 2000 | Bridge Signal K ↔ N2K |
| 6 | Chartplotter (×2) | B&G Vulcan 7 FS | NMEA 2000 | PORT (helm) + STBD (nav) — LEN 1+1 |
| 7 | Batterie | SOK SK12V100PC LiFePO4 | Bluetooth LE | Monitoring BMS (direct InfluxDB) |
| 8 | Baromètre | Yacht Devices YDBC-05 | NMEA 2000 | Pression atmosphérique |
| 9 | Transpondeur AIS | B&G AIS700 Class B | NMEA 2000 | AIS TX/RX + sécurité |
| 10 | Loch / Sonde / Temp eau | Airmar DST810 | NMEA 2000 | STW + profondeur + température eau |

### 2.3 Bus NMEA 2000 — Charge réseau

| Appareil | LEN | Rôle sur le bus |
|----------|-----|----------------|
| YDNU-02 Gateway | 1 | Bridge USB ↔ N2K |
| Vulcan 7 FS | 1 | Chartplotter + réception données |
| WS320 Base Station | 2 | Émetteur vent via BLE→N2K |
| YDBC-05 Barometer | 1 | Émetteur pression |
| AIS700 | 1 | Transpondeur AIS |
| **Total** | **7 / 50 LEN max** | ✅ (14% — 43 slots free) |

---

## 3. RÉSEAUX PHYSIQUES

### 3.1 USB (série)

```
RPi 4 USB-A
  └── /dev/ttyACM0 ──► YDNU-02 (CDC ACM, VID:0483 PID:A217)
                           │
                           └── NMEA 2000 backbone (250 kbps)

RPi 4 USB-A
  └── /dev/ttyUSB0 ──► UM982 GNSS (CH340/CP2102, 115200 baud, 8N1)
```

> ⚠️ YDNU-02 utilise le driver CDC ACM (pas FTDI) → port `/dev/ttyACM*`  
> ⚠️ UM982 utilise un convertisseur USB-série → port `/dev/ttyUSB*`

### 3.2 Bluetooth LE (hci0)

```
RPi 4 BLE adapter (hci0)
  ├── WIT WT901BLECL    ← IMU (BLE 5.0, device: "WT901BLE__")
  ├── Calypso UP10      ← Anémomètre (BLE 4.x, device: "ULTRASONIC")
  └── SOK Battery BMS   ← BMS LiFePO4 (BLE, JBD protocol)
```

**Services systemd associés :**

| Service | Instrument | Rôle |
|---------|-----------|------|
| `signalk.service` | WIT (via plugin) | Lecture IMU, injection SK |
| `calypso_direct` | Calypso UP10 | Lecture vent BLE → UDP 4123 |
| `calypso_watchdog` (obsolète) | Calypso UP10 | Redémarrage auto si déconnexion |
| `sok_direct` | SOK BMS | Lecture BMS → direct InfluxDB |

### 3.3 NMEA 2000 (backbone bateau)

```
YDNU-02 ──T── Vulcan 7 FS
         │
         ├──T── WS320 Base Station
         │
         ├──T── YDBC-05 Barometer
         │
         ├──T── AIS700
         │
         [T] Terminateurs aux deux extrémités
```

### 3.4 Réseau IP (WiFi)

```
RPi 4 (midnightrider.local)
  ├── Point d'accès WiFi (hostapd)
  │     SSID: MidnightRider / password: voir wifi-ap.txt
  │     Connecté: téléphones équipage, tablettes
  │
  └── Cloudflare Tunnel ──► Internet (accès distant sécurisé)
```

---

## 4. STACK LOGICIELLE

### 4.1 Services et ports

| Service | Port | Protocole | Mode de démarrage | Technologie |
|---------|------|-----------|------------------|-------------|
| **Signal K** | 3000 | HTTP/WS | `systemctl` (**JAMAIS docker**) | Node.js |
| **InfluxDB** | 8086 | HTTP | `docker compose` | Docker |
| **Grafana** | 3001 | HTTP | `docker compose` | Docker |
| **OpenClaw Gateway** | 18789 | HTTP | `systemctl` | Local only |
| **Regatta Server** | 5000 | HTTP | `docker compose` | Docker |
| **Signal K UDP RX** | 4123 | UDP | Interne Signal K | Calypso injection |

> ⚠️ **RÈGLE ABSOLUE :**  
> Signal K = `systemctl` UNIQUEMENT  
> InfluxDB + Grafana = `docker compose` UNIQUEMENT  
> Ne jamais inverser ces deux règles.

### 4.2 Signal K — Plugins actifs

| Plugin | Rôle | Source SK |
|--------|------|-----------|
| `signalk-um982-gnss` | Lecture UM982 (NMEA+proprietary) | `signalk-um982-gnss.UM982-HDG` |
| `signalk-wit-imu-ble` | Lecture WIT IMU BLE | `signalk-wit-imu-ble.XX` |
| `sk-to-nmea2000` (npm) | Émission PGNs → YDNU-02 → N2K (7 actifs) | ✅ OPERATIONAL |
| `signalk-to-influxdb2` | Persistence SK → InfluxDB | — |
| `signalk-performance-polars` | Calcul VMG, efficacité polaire | `performance.*` |
| signalk-heading-true-calculator | Cap vrai (HM + variation mag.) | navigation.headingTrue |
| signalk-j30-leeway | Dérive J/30 = K×|gîte|/STW² | performance.leewayAngle |
| signalk-current-calculator | Courant (set + drift) | environment.current.* |
| signalk-truewind-calculator | Vent vrai (TWD/TWS/TWA) | environment.wind.* |
| `signalk-astronomical` | Données soleil/lune | `environment.sun.*` |
| `signalk-rpi-cpu-temp` | Temp CPU RPi | `environment.rpi.*` |
| `signalk-sails-management-v2` | Gestion voiles | `sails.*` |
| `signalk-app-dock` | Dashboard Signal K webapp | — |
| `signalk-to-nmea0183` | Export NMEA 0183 (WiFi) | — |
| `freeboard-sk` | Carte nautique webapp | — |
| `kip` | Instrument display webapp | — |
| `course-provider` | Calculs de navigation | — |

### 4.3 Docker Compose — Services

```yaml
# docker-compose.yml — résumé
services:
  influxdb:
    image: influxdb:2.x
    ports: ["8086:8086"]
    volumes: [influxdb-data:/var/lib/influxdb2]

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    volumes: [grafana-data:/var/lib/grafana]
    depends_on: [influxdb]

  regatta-server:
    ports: ["5000:5000"]
```

### 4.4 InfluxDB — Organisation des données

| Paramètre | Valeur |
|-----------|--------|
| **Organisation** | MidnightRider |
| **Bucket principal** | `midnight_rider` |
| **Rétention** | Illimitée (racing data) |
| **Token** | Stocké dans `.env` (jamais dans git) |

**Measurements clés :**

| Measurement | Source | Champs principaux |
|-------------|--------|------------------|
| `navigation` | Signal K → signalk-to-influxdb2 | headingTrue, position, SOG, COG |
| `environment` | Signal K → signalk-to-influxdb2 | wind.*, outside.*, water.* |
| `attitude` | Signal K → signalk-to-influxdb2 | roll, pitch |
| `performance` | Signal K → signalk-to-influxdb2 | targetSpeed, polarEfficiency, VMG |
| `sok_bms` | Python direct | soc_pct, voltage_v, current_a, cell_1_4_mv |
| `astronomical` | signalk-astronomical | sunrise, sunset, moon phase |
| `sails` | signalk-sails-management | active_sail, reef_state |

### 4.5 Grafana — Dashboards

| # | Nom | Contenu |
|---|-----|---------|
| 01 | Cockpit | Cap, position, SOG, COG, gîte |
| 02 | Environment | Vent (AWS/TWS/AWA/TWA), pression baro, temp |
| 03 | Performance | Polaires, VMG, efficacité, target speed |
| 04 | Wind & Current | Vent détaillé, courant estimé |
| 05 | Competitive | Données course, laylines |
| 06 | Electrical | SOK BMS — SoC, tension, cellules, température |
| 07 | Race | Dashboard régate complet |
| 08 | Alerts | Alertes actives et historique |
| 09 | Crew | Dashboard équipage (vue simplifiée) |

---

---

## 4.6 MediaMan (Telegram Reporter) — Foundation Phase

**Status:** FOUNDATION ONLY — DRY-RUN VALIDATED — PRODUCTION NOT AUTHORIZED

**Current State (2026-08-27):**
- ✅ SQLite delivery state machine (PENDING → SENDING → SENT / FAILED)
- ✅ Telegram sender (outbound-only, no inbound)
- ✅ Logging infrastructure (structured, sanitized)
- ✅ Systemd units present (service + timer disabled)
- ❌ Real content provider not implemented
- ❌ OpenClaw LLM adapter not implemented
- ⏳ Telegram bot/group not created

**Key Properties:**
- One-way outbound only (no inbound Telegram processing, webhook, polling, or getUpdates)
- No Signal K modifications required
- No Docker service changes
- No Portal or Regatta endpoint exposure
- Fail-closed: invalid content → skip send (never fake article)

**Production Blockers:**
- Real content provider (LLM adapter) not implemented
- OpenClaw CLI integration not implemented
- No explicit Denis approval for production activation

**Systemd Units (Disabled):**
- `mediaman.service` — one-shot execution
- `mediaman.timer` — 15-minute intervals (NOT enabled)

**Configuration:**
- Environment: `/etc/mediaman/mediaman.env` (not version-controlled)
- State: SQLite at `/var/lib/mediaman/state.sqlite3` (runtime only)
- Logs: `/var/log/mediaman/mediaman.log` (structured, sanitized)

**For Details:** See [docs/INTEGRATION/TELEGRAM-REPORTER-INTEGRATION-GUIDE.md](../INTEGRATION/TELEGRAM-REPORTER-INTEGRATION-GUIDE.md)

### 4.7 MCPCollector (Navigation Facts) — Step 3A

**Status:** ✅ COMPLETE — Mocked unit tests passing (178/178 full suite)

**Boundary:** MCPClient → MCPCollector → validated structured navigation facts

**Source-Verified Tools:**

| Public ID | Wire Name | Server | Freshness | Status |
|---|---|---|---|---|
| `racing.get_position` | `get_position` | racing | 30 sec | ✅ Verified |
| `racing.get_sog` | `get_sog` | racing | 15 sec | ✅ Verified |
| `racing.get_cog` | `get_cog` | racing | 15 sec | ✅ Verified |

**Key Properties:**

- Provenance tracking: tool_public_id, server_name, wire_tool_name, source_id, timestamps, freshness
- Source timestamp preservation (never fabricated)
- Observed_at distinct from source_timestamp
- Fail-closed semantics: stale facts block COMPLETE status
- Freshness validation: ISO 8601 UTC (Z and explicit offset), deterministic reference_time injection
- Field validation: latitude (-90 to 90), longitude (-180 to 180), SOG (non-negative), COG (0-360°)
- LLM-safe serialization: exact coordinates suppressed in `to_llm_context()`
- Structured logging: STARTUP, DATA_IN, DATA_OUT, ERROR, SHUTDOWN events
- Log output: exact coordinates, raw payloads, credentials never logged

**Test Evidence (Mocked Unit Tests):**

- MCP client tests: 41/41 PASSED
- Collector tests: 32/32 PASSED (26 original + 6 evidence-closure tests)
- Full MediaMan suite: 178/178 PASSED (includes nested tests above)
- All tests are mocked unit tests with no runtime E2E verification
- Real MCPClient compatibility verified with subprocess mocked
- Logging output verified (no exact coordinates or credentials)
- Freshness edge cases verified (future, malformed, stale timestamps)
- LLM-safe serialization verified (coordinate suppression)

**Not Implemented at This Stage:**
- SQLite event queue
- OpenClaw adapter
- Telegram integration
- Timer activation

**For Details:** `mediaman/mcp_collector.py` and `tests/mediaman/test_mcp_collector.py`

### 4.8 EventDetector (Deterministic Transitions) — Step 4A

**Status:** ✅ COMPLETE — Mocked unit tests passing (14/14 detector + 192/192 full suite)

**Boundary:** MCPCollector output (CollectionResult) → EventDetector → DetectedEvent list

**Event Types:**

| Event Type | Trigger | Severity | Details |
|---|---|---|---|
| NAVIGATION_DATA_LOST | COMPLETE → PARTIAL/FAILED | WARNING | Collection status degraded |
| NAVIGATION_DATA_RECOVERED | PARTIAL → COMPLETE | INFO | Collection status recovered |
| FACT_BECAME_STALE | valid → stale | WARNING | Individual fact freshness exceeded |
| FACT_BECAME_INVALID | valid → invalid | ERROR | Individual fact validation failed |
| FACT_RECOVERED | stale/missing/invalid → valid | INFO | Individual fact recovered |

**Key Properties:**

- **Deterministic input:** previous CollectionResult (optional) + current CollectionResult + observed_at timestamp
- **No transition fabrication:** if previous is None, no events emitted (initial observation is side-effect-free)
- **Fail-closed semantics:** stale/invalid facts never upgraded to valid; missing values not replaced
- **Deterministic event IDs:** SHA256-based hash of (race_id, event_type, field_name, observed_at) — no random UUIDs
- **Coordinate suppression:** exact latitude/longitude never appear in event payloads
- **Input immutability:** detector does not modify previous or current CollectionResult
- **No external side effects:** pure function; no file I/O, network access, or subprocess calls

**Test Evidence (Mocked Unit Tests):**

- EventDetector tests: 14/14 PASSED
  - No previous result → no fabricated events
  - Collection-level transitions (COMPLETE ↔ PARTIAL)
  - Fact-level transitions (valid → stale → recovered)
  - Event ID determinism
  - Coordinate suppression in payloads
  - Input immutability
  - Malformed input handled gracefully
  - Real CollectionResult/NavigationFact objects (not mocks)

- MCP client tests: 41/41 PASSED (unchanged from Step 3A)
- Collector tests: 32/32 PASSED (unchanged from Step 3A)
- Full MediaMan suite: 192/192 PASSED (includes all above)

**All tests are mocked unit tests with no runtime E2E verification.**

**Not Implemented at This Stage:**
- SQLite event queue (Step 4B)
- OpenClaw LLM adapter (Step 4C)
- Telegram reporter (Step 4D)
- Timer or scheduler (Step 4E)
- Runtime service wrapper

**For Details:** `mediaman/event_detector.py` and `tests/mediaman/test_event_detector.py`

### 4.9 EventQueue (Durable Local SQLite) — Step 4B

**Status:** ✅ COMPLETE — Offline unit tests passing (19/19 queue tests, 211/211 full suite)

**Boundary:** EventDetector output (DetectedEvent list) → EventQueue → queued events ready for delivery

**Architecture:**

EventQueue is a local SQLite library component (no daemon, no network access, no subprocess calls). It receives DetectedEvent objects from EventDetector and stores them durably for later delivery.

**Key Properties:**

- **Idempotency:** Events enqueued by event_id. Duplicate enqueue does not reset state or retry attempts.
- **Statuses:** PENDING (ready to claim), PROCESSING (claimed, locked), SENT (delivery succeeded), FAILED (retry pending), DEAD_LETTER (max retries exceeded).
- **Claiming:** Transactional SELECT with lease acquisition. Claimed events are locked by expiration time. Bounded claim size.
- **Lease Recovery:** Expired PROCESSING locks automatically release back to PENDING.
- **Retry Scheduling:** Deterministic exponential backoff (2^attempts seconds, capped at 3600s). Max attempt count configurable (default 5).
- **Sensitive Payload Rejection:** Validates event payloads before enqueue—rejects exact latitude/longitude, raw MCP envelopes, tokens, credentials, passwords, connection strings.
- **Row Mapping:** Named-column access (sqlite3.Row factory) instead of positional unpacking. All fields mapped explicitly via _row_to_queued_event() helper.
- **Persistence:** Events survive queue close and reopen. Schema created automatically on initialize().
- **Offline Testing:** No external services contacted. Tests use temporary SQLite databases or :memory:.

**Database Schema:**

| Column | Type | Role |
|--------|------|------|
| event_id | TEXT PRIMARY KEY | Idempotency key |
| event_type | TEXT | Navigation data lost, fact stale, etc. |
| observed_at | TEXT | Detector observation timestamp |
| source_timestamp | TEXT | Original fact timestamp (nullable) |
| race_id | TEXT | Race context (nullable) |
| severity | TEXT | INFO, WARNING, ERROR |
| affected_field | TEXT | Field name if applicable (nullable) |
| payload_json | TEXT | Sanitized event data |
| status | TEXT | PENDING, PROCESSING, SENT, FAILED, DEAD_LETTER |
| attempts | INTEGER | Retry count |
| next_attempt_at | TEXT | Backoff deadline (ISO 8601 UTC) |
| locked_until | TEXT | Lease expiration (ISO 8601 UTC, nullable) |
| last_error | TEXT | Sanitized error message (max 200 chars, nullable) |
| created_at | TEXT | Insertion timestamp |
| updated_at | TEXT | Last modification timestamp |

**Public Methods:**

- `enqueue(event: DetectedEvent) → bool` — Insert or skip (idempotent)
- `claim(count: int, lock_duration_seconds: int) → List[QueuedEvent]` — Fetch due PENDING, lock as PROCESSING
- `mark_sent(event_id: str) → bool` — Transition to SENT
- `mark_failed(event_id: str, error: str, max_attempts: int) → bool` — Increment attempts, schedule retry or DEAD_LETTER
- `release_expired_leases() → int` — Move expired PROCESSING back to PENDING
- `get_event(event_id: str) → Optional[QueuedEvent]` — Retrieve single event
- `count_by_status(status: str) → int` — Event count by status
- `close()` — Clean database close

**Test Evidence (Offline Unit Tests):**

- EventQueue tests: 19/19 PASSED
  - Schema creation
  - Valid enqueue (PENDING status, zero attempts)
  - Duplicate enqueue idempotency
  - Duplicate enqueue preserving SENT status
  - Coordinate rejection (exact latitude/longitude)
  - Credential rejection (tokens, passwords)
  - Due event claim (status → PROCESSING)
  - Claim bounded size
  - Lease creation and expiration
  - Expired lease recovery (PROCESSING → PENDING)
  - Mark sent (idempotent)
  - Mark failed with retry scheduling
  - Deterministic exponential backoff
  - Dead letter transition after max attempts
  - Sanitized error storage (no credentials in last_error)
  - Persistence after close and reopen
  - Transaction rollback on error
  - Input immutability
  - Compatibility with DetectedEvent output
  - Count by status
  - No network access
  - No subprocess access

- Full MediaMan suite: 211/211 PASSED (includes all above + Steps 3A/4A)
- All tests are mocked unit tests with no runtime E2E verification
- Uses temporary SQLite databases for test isolation

**Not Implemented at This Stage:**

- OpenClaw LLM adapter (Step 4C)
- Telegram reporter (Step 4D)
- Timer or scheduler activation (Step 4E)
- Runtime service wrapper
- Production database initialization

**For Details:** `mediaman/event_queue.py` and `tests/mediaman/test_event_queue.py`

### 4.10 EventOrchestrator (Safe Event Processing) — Step 4D

**Status:** ✅ COMPLETE — Hardened implementation with strict validation and error redaction (303/303 full suite tests passing)

**Boundary:** EventQueue output (QueuedEvent) → EventOrchestrator → OpenClawAdapter.generate_article() → mark_sent() or mark_failed()

**Architecture:**

```
EventQueue.claim(count=1)
    ↓ (exactly one event per cycle)
SafePromptBuilder validation (strict type checks, injection resistance)
    ↓ (fail-closed on invalid input)
OpenClawAdapter.generate_article(prompt)
    ↓ (never QueuedEvent or payload_json)
Result handling
    ├── Success: mark_sent() → internal content only
    └── Failure: mark_failed(safe_classification)
```

**Key Properties:**

- **Single-event processing:** EventQueue.claim(count=1), exactly one event per orchestration cycle
- **Strict validation before logging:** All field types validated in SafePromptBuilder before any log output
- **Safe-field allowlist:** event_type, race_id, severity, observed_at, source_timestamp, affected_field (only)
- **Prompt injection rejection:** Rejects control characters, newlines, and instruction patterns ("ignore previous instructions", "system message", etc.)
- **Type validation fail-closed:** Invalid types (int, list, bool, dict, float) rejected with ValueError at validation time, not via str() conversion
- **ErrorSanitizer comprehensive coverage:**
  - Key=value patterns: secret=, credential=, token=, api_key=, password=, authorization=, bearer
  - JWT-like values: eyJ[...]
  - All URI schemes with credentials: postgres://, postgresql://, mysql://, redis://, mongodb://, amqp(s)://, http(s)://
  - Coordinates: lat/lon patterns
  - All redactions occur before truncation
- **Orchestrator state ownership:** mark_sent() and mark_failed() called only by EventOrchestrator
- **EventQueue retry ownership:** Retry scheduling, next_attempt_at, exponential backoff, DEAD_LETTER escalation (EventQueue responsibility)
- **Internal content only:** Result.content returned for internal use only, never passed to external systems
- **No Telegram integration:** Telegram code NOT IMPLEMENTED; no external publication
- **Safe logging:** No raw event values, no raw exception messages, no raw adapter errors logged

**Test Evidence (Mocked Unit Tests):**

- EventOrchestrator tests: 13/13 PASSED
  - Type validation: 6 tests (reject int, list, bool, dict, float, non-string types)
  - Prompt injection: 5 tests (reject control chars, newlines, instruction patterns)
  - Sensitive fields: 3 tests (reject all 16 sensitive field names + variants)
  - Error sanitization: 8 tests (secret=, credential=, HTTP/HTTPS URIs, postgres, mysql, redis, mongodb, amqp)
  - Flow safety: 8 tests (no raw event fields before validation, no raw exceptions in logs, safe classifications only)
- EventQueue tests: 79/79 PASSED (unchanged from Step 4B.2)
- OpenClawAdapter tests: 26/26 PASSED (unchanged from Step 4C)
- Full MediaMan suite: 303/303 PASSED
- All tests are mocked unit tests with no runtime E2E verification
- No live OpenClaw Gateway contact, no MCP contact, no Signal K modification

**Hardening Details:**

- **Pre-validation logging safety:** Logs only event_id before SafePromptBuilder validation; no raw event_type, race_id, severity, payload_json
- **Exception handling:** Exception class name only (never exception message or adapter.error)
- **Error classifications:** Safe deterministic categories (prompt_validation_failed, prompt_construction_error, adapter_unavailable, adapter_timeout, adapter_connection_error, adapter_auth_error, adapter_error)
- **Prompt construction:** Never forwards raw payload_json, never includes coordinates, never includes credentials, never includes free-text fields
- **Sanitization before logging:** ErrorSanitizer.sanitize() redacts all sensitive patterns before any logger call

**Not Implemented at This Stage:**

- Telegram integration (explicitly deferred)
- External content publication
- Runtime E2E validation
- Service activation or timer scheduling
- Production database initialization

**For Details:** `mediaman/event_orchestrator.py` and `tests/mediaman/test_event_orchestrator.py`

## 5. FLUX DE DONNÉES DÉTAILLÉS

### 5.1 Cap vrai (headingTrue)

```
UM982 GNSS (ANT1 + ANT2)
  HEADINGOFFSET 90 appliqué (firmware permanent, NVRAM, 2026-05-17)
  ↓ USB /dev/ttyUSB0 (115200 baud)
signalk-um982-gnss plugin
  ↓ Signal K — navigation.headingTrue (radians)
  ├──► InfluxDB → Grafana 01-Cockpit
  └──► sk-to-nmea2000 (npm)
         ↓ PGN 127250 (Vessel Heading)
         YDNU-02 → N2K bus
         └── Vulcan 7 FS (affichage helm)
```

### 5.2 Gîte / Assiette (attitude)

```
WIT WT901BLECL (BLE 5.0, 30 Hz)
  ↓ wit-ble-direct.py → quaternion → Euler transformation
  ↓ Signal K — navigation.attitude.{roll, pitch}
  │              navigation.headingMagnetic (magnetic heading)
  │              navigation.acceleration.{x, y, z}
  │              navigation.rateOfTurn
  ├──► InfluxDB → Grafana 01-Cockpit
  ├──► Wave Analyzer v1.1 (heel correction)
  │       ↓ environment.water.waves.*
  └──► sk-to-nmea2000 (npm)
         ↓ PGN 127257 (Attitude)    ← attitude.js patché 2026-05-17
         YDNU-02 → N2K bus
         └── Vulcan 7 FS (affichage gîte en temps réel)
```

### 5.3 Vent (priorité sources)

```
Calypso UP10 (BLE → UDP 4123) — PRIORITÉ 1 pour Signal K
  ↓ calypso-anemometer Python (systemd)
  ↓ Signal K Delta UDP port 4123
  ↓ environment.wind.{speedApparent, angleApparent, speedTrue, directionTrue}
  ├──► InfluxDB → Grafana 02-Environment
  └──► sk-to-nmea2000 (npm) → PGN 130306 → Vulcan 7

B&G WS320 (BLE → base station → N2K) — PRIORITÉ 2 pour Signal K
  ↓ NMEA 2000 PGN 130306 (5 Hz) — DIRECT vers Vulcan 7 FS
  └──► YDNU-02 → Signal K (source secondaire)
```

### 5.4 Position GPS

```
UM982 GNSS (Primary — 1.5m accuracy autonomous)
  ↓ PGNs 129025, 129026, 129029 → Signal K → InfluxDB → Grafana

Vulcan 7 FS internal GPS (Fallback — 3m accuracy)
  ↓ PGNs 129025, 129026 sur N2K bus (si UM982 absent)
```

### 5.5 Batterie (SOK BMS)

```
SOK SK12V100PC BMS (BLE — JBD protocol)
  ↓ sok_bms_reader.py (Python, 0.2 Hz)
  ↓ DIRECT → InfluxDB measurement: sok_bms
  [Signal K non impliqué — bypass intentionnel]
  └──► Grafana 06-Electrical
```

### 5.6 Pression atmosphérique

```
YDBC-05 (N2K PGNs 130310/130311/130314 @ 0.5 Hz)
  ↓ N2K bus → YDNU-02 → Signal K
  ↓ environment.outside.pressure (Pascal)
  ├──► InfluxDB → Grafana 02-Environment
  └──► Vulcan 7 FS (page données environnement)
```

### 5.7 AIS

```
AIS700 Class B (N2K PGNs 129038–129810)
  ↓ N2K bus → YDNU-02 → Signal K
  ↓ vessels.<MMSI>.{name, position, SOG, COG, ...}
  ├──► InfluxDB (log trafic AIS)
  └──► Vulcan 7 FS (targets sur carte)
```

---

### 5.6 AIS Competitor Tracker (`ais/`)

Added Phase J-1 (2026-06-15). Real-time competitor tracking via Signal K AIS.

| File | Role |
|------|------|
| `ais/__init__.py` | Package marker |
| `ais/ais_lib.py` | Math library: haversine, bearing, TWA, VMG wind/mark, delta, color logic |
| `ais/competitors_db.py` | CompetitorDB: load/enrich/search from regatta/competitors.json, TTL 5min |
| `ais/ais_watch.py` | Optional daemon: polls Signal K every 30s, writes to InfluxDB measurement `competitor_tracking` |
| `ais/server_handlers.py` | API handlers: `api_competitors()` + `api_fleet_db()` (imported via /repo/ais in Docker) |

**API Endpoints** (regatta port 5000):
- `GET /api/competitors?radius_nm=10&min_sog_kts=0&vmg_mode=wind|mark&include_unknown=false`
  Returns competitors within radius with TWA, VMG wind/mark, color (GREEN/RED/NEUTRAL)
- `GET /api/fleet_db`
  Returns all 68 boats with AIS status (live/stale/old/absent)

**Color Logic**: GREEN = VMG_MR > VMG_comp (gaining ground) | RED = VMG_comp > VMG_MR (losing ground) | NEUTRAL = equal or unknown

**Database**: 68 total boats, 56 active, 56 with MMSI (from `regatta/competitors.json`)

## 6. PRIORITÉS DES SOURCES SIGNAL K

| Path Signal K | Priorité 1 (haute) | Priorité 2 | Priorité 3 |
|---------------|-------------------|-----------|-----------|
| `navigation.position` | UM982 | Vulcan 7 internal GPS | — |
| `navigation.headingTrue` | UM982 | — | — |
| `navigation.speedOverGround` | UM982 | Vulcan 7 | — |
| `navigation.attitude.*` | **WIT IMU** | Calypso (si --compass=on) | — |
| `navigation.rateOfTurn` | WIT IMU | UM982 dual-antenna | — |
| `environment.wind.*` | **Calypso UP10** | WS320 (via N2K) | — |
| `environment.outside.temperature` | Calypso UP10 | YDBC-05 | — |
| `environment.outside.pressure` | YDBC-05 | — | — |
| `vessels.*` (AIS) | AIS700 | — | — |

---

## 7. UNITÉS SI — RÉFÉRENCE RAPIDE

| Grandeur | Unité Signal K | Affichage Grafana | Conversion |
|----------|---------------|------------------|-----------|
| Vitesse (SOG, vent) | m/s | nœuds | × 1.944 |
| Cap, angle | radians | degrés | × 57.296 |
| Température | Kelvin | °C | − 273.15 |
| Pression | Pascal | hPa | ÷ 100 |
| Taux de giration | rad/s | °/s | × 57.296 |
| État de charge | ratio 0–1 | % | × 100 |
| Position | degrés décimaux | degrés décimaux | — |

---

## 9. RÈGLES ABSOLUES — OPÉRATION OC

> Ces règles s'appliquent à tout prompt généré par Dust/OC.  
> Aucune exception sans validation explicite de Denis.

| # | Règle | Raison |
|---|-------|--------|
| 1 | Signal K = `systemctl` UNIQUEMENT | Port 3000, service natif |
| 2 | InfluxDB = Docker UNIQUEMENT | Port 8086, container |
| 3 | Grafana = Docker UNIQUEMENT | Port 3001, container |
| 4 | Fichiers JSON = `python3` UNIQUEMENT | Jamais `sed` sur du JSON |
| 5 | Aucun token/secret dans `git commit` | Sécurité |
| 6 | Après chaque action : `git add -A && git commit -m '...' && git push` | Traçabilité |
| 7 | Changement structurel = validation Denis avant exécution | Sécurité |
| 8 | `HEADINGOFFSET 90` dans UM982 NVRAM = NE PAS écraser | Permanent, critique |
| 9 | `attitude.js` patché (2026-05-17) = référence actuelle | PGN 127257 actif |
| 10 | SOK BMS → direct InfluxDB (bypass Signal K) | Architecture volontaire |

---



---

## 8. SIGNAL K — SOURCES ET PRIORITÉS (mis à jour 2026-06-15)

> Ces sections sont fusionnées depuis `docs/HARDWARE/INSTRUMENT-INVENTORY.md`.
> Pour la topologie complète du bus N2K et la matrice des flux PGN, voir le fichier canonical :
> 📌 **`docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`**

### 8.1 Inventaire des sources Signal K

| # | Instrument | Modèle | Protocole | Source Signal K | Fréquence | État |
|---|------------|--------|-----------|-----------------|-----------|------|
| 1 | GPS + Cap vrai | Unicore UM982 | NMEA 0183 / USB | `signalk-um982-gnss.UM982-HDG` | 1 Hz | ✅ Actif |
| 2 | IMU | WIT WT901BLECL | Bluetooth LE | `signalk-wit-imu-ble.XX` | 10 Hz | ✅ Actif |
| 3 | Vent masthead | Calypso UP10 | Bluetooth LE | `calypso-up10` (UDP:4123) | 1 Hz | ✅ Actif |
| 4 | Vent masthead (N2K) | B&G WS320 | NMEA 2000 | `nmea2000_ws320` | 5 Hz | ✅ Actif |
| 5 | Gateway N2K | Yacht Devices YDNU-02 | USB / N2K | transparent | N/A | ✅ Actif |
| 6 | Chartplotter | B&G Vulcan 7 FS | NMEA 2000 | `vulcan_internal` | 1 Hz | ✅ Actif |
| 7 | Systèmes RPi | Raspberry Pi 4 | Interne | `signalk-system-stats` | 0.2 Hz | ✅ Actif |
| 8 | Batterie | SOK BMS LiFePO4 | Bluetooth LE | Direct InfluxDB (bypass SK) | 0.2 Hz | ✅ Actif |
| 9 | Baromètre | Yacht Devices YDBC-05 | NMEA 2000 | `nmea2000_ydbc05` | 0.5 Hz | ✅ Actif |
| 10 | Transpondeur AIS | B&G AIS700 Class B | NMEA 2000 | `nmea2000_ais700` | event-driven | ✅ Actif |

### 8.2 Noms des sources Signal K

## Signal K Source Name Reference

| Signal K Source | Instrument | Notes |
|-----------------|------------|-------|
| `signalk-um982-gnss.UM982-HDG` | Unicore UM982 | Proprietary #UNIHEADING sentences — dual-antenna heading. HEADINGOFFSET 90 applied 2026-05-17 |
| `signalk-wit-imu-ble.XX` | WIT WT901BLECL | Hull mount, 30 Hz — primary attitude source (highest SK priority) |
| `nmea2000_ws320` | B&G WS320 | Apparent wind via N2K backbone → YDNU-02 → SK. Also feeds Vulcan 7 directly at 5 Hz |
| `calypso-up10` | Calypso UP10 | Primary SK wind source (BLE → UDP port 4123). Active via systemd service |
| `vulcan_internal` | B&G Vulcan 7 FS | Secondary GPS/COG/SOG from Vulcan internal GNSS |
| `signalk-system-stats` | Raspberry Pi 4 | CPU temp (K), load, RAM |
| `nmea2000_ydbc05` | Yacht Devices YDBC-05 | Atmospheric pressure via N2K → YDNU-02 → SK |
| `nmea2000_ais700` | B&G AIS700 | AIS vessel targets via N2K → YDNU-02 → SK (`vessels.*` namespace) |
| `sok_bms` | SOK Battery BMS | Direct InfluxDB — bypasses Signal K entirely |

---

### 8.3 Priorités de source — Vent
## Wind Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `calypso-up10` | `environment.wind.*` | Primary — masthead BLE sensor, 1 Hz |
| 2 | `nmea2000_ws320` | `environment.wind.*` | Secondary — N2K via YDNU-02, 5 Hz |

> The WS320 also feeds the Vulcan 7 FS **directly** at 5 Hz without going through Signal K
> (N2K backbone shortcut). The Vulcan uses this for real-time sail trim display.

### 8.4 Priorités de source — Attitude
## Attitude Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `signalk-wit-imu-ble.XX` | `navigation.attitude.*` | WIT IMU — 30 Hz. Also feeds PGN 127257 → Vulcan 7 via YDNU-02 |
| 2 | `calypso-up10` | `navigation.attitude.*` | Compass mode only (if `--compass=on`) — overridden by WIT |

---

### 8.5 Non installés
## Not Installed

| # | Instrument | Role | Notes |
|---|------------|------|-------|
| 11 | Speed through water (STW) / loch | Boat speed, leeway | Via NMEA 2000 → YDNU-02 when installed |
| 12 | Depth sounder | Depth, water temperature | Via NMEA 2000 → YDNU-02 when installed |

---

## 10. SÉCURITÉ

#

---

## 8. SIGNAL K — SOURCES ET PRIORITÉS (mis à jour 2026-06-15)

> Ces sections sont fusionnées depuis `docs/HARDWARE/INSTRUMENT-INVENTORY.md`.
> Pour la topologie complète du bus N2K et la matrice des flux PGN, voir le fichier canonical :
> 📌 **`docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`**

### 8.1 Inventaire des sources Signal K

| # | Instrument | Modèle | Protocole | Source Signal K | Fréquence | État |
|---|------------|--------|-----------|-----------------|-----------|------|
| 1 | GPS + Cap vrai | Unicore UM982 | NMEA 0183 / USB | `signalk-um982-gnss.UM982-HDG` | 1 Hz | ✅ Actif |
| 2 | IMU | WIT WT901BLECL | Bluetooth LE | `signalk-wit-imu-ble.XX` | 10 Hz | ✅ Actif |
| 3 | Vent masthead | Calypso UP10 | Bluetooth LE | `calypso-up10` (UDP:4123) | 1 Hz | ✅ Actif |
| 4 | Vent masthead (N2K) | B&G WS320 | NMEA 2000 | `nmea2000_ws320` | 5 Hz | ✅ Actif |
| 5 | Gateway N2K | Yacht Devices YDNU-02 | USB / N2K | transparent | N/A | ✅ Actif |
| 6 | Chartplotter | B&G Vulcan 7 FS | NMEA 2000 | `vulcan_internal` | 1 Hz | ✅ Actif |
| 7 | Systèmes RPi | Raspberry Pi 4 | Interne | `signalk-system-stats` | 0.2 Hz | ✅ Actif |
| 8 | Batterie | SOK BMS LiFePO4 | Bluetooth LE | Direct InfluxDB (bypass SK) | 0.2 Hz | ✅ Actif |
| 9 | Baromètre | Yacht Devices YDBC-05 | NMEA 2000 | `nmea2000_ydbc05` | 0.5 Hz | ✅ Actif |
| 10 | Transpondeur AIS | B&G AIS700 Class B | NMEA 2000 | `nmea2000_ais700` | event-driven | ✅ Actif |

### 8.2 Noms des sources Signal K

## Signal K Source Name Reference

| Signal K Source | Instrument | Notes |
|-----------------|------------|-------|
| `signalk-um982-gnss.UM982-HDG` | Unicore UM982 | Proprietary #UNIHEADING sentences — dual-antenna heading. HEADINGOFFSET 90 applied 2026-05-17 |
| `signalk-wit-imu-ble.XX` | WIT WT901BLECL | Hull mount, 30 Hz — primary attitude source (highest SK priority) |
| `nmea2000_ws320` | B&G WS320 | Apparent wind via N2K backbone → YDNU-02 → SK. Also feeds Vulcan 7 directly at 5 Hz |
| `calypso-up10` | Calypso UP10 | Primary SK wind source (BLE → UDP port 4123). Active via systemd service |
| `vulcan_internal` | B&G Vulcan 7 FS | Secondary GPS/COG/SOG from Vulcan internal GNSS |
| `signalk-system-stats` | Raspberry Pi 4 | CPU temp (K), load, RAM |
| `nmea2000_ydbc05` | Yacht Devices YDBC-05 | Atmospheric pressure via N2K → YDNU-02 → SK |
| `nmea2000_ais700` | B&G AIS700 | AIS vessel targets via N2K → YDNU-02 → SK (`vessels.*` namespace) |
| `sok_bms` | SOK Battery BMS | Direct InfluxDB — bypasses Signal K entirely |

---

### 8.3 Priorités de source — Vent
## Wind Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `calypso-up10` | `environment.wind.*` | Primary — masthead BLE sensor, 1 Hz |
| 2 | `nmea2000_ws320` | `environment.wind.*` | Secondary — N2K via YDNU-02, 5 Hz |

> The WS320 also feeds the Vulcan 7 FS **directly** at 5 Hz without going through Signal K
> (N2K backbone shortcut). The Vulcan uses this for real-time sail trim display.

### 8.4 Priorités de source — Attitude
## Attitude Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `signalk-wit-imu-ble.XX` | `navigation.attitude.*` | WIT IMU — 30 Hz. Also feeds PGN 127257 → Vulcan 7 via YDNU-02 |
| 2 | `calypso-up10` | `navigation.attitude.*` | Compass mode only (if `--compass=on`) — overridden by WIT |

---

### 8.5 Non installés
## Not Installed

| # | Instrument | Role | Notes |
|---|------------|------|-------|
| 11 | Speed through water (STW) / loch | Boat speed, leeway | Via NMEA 2000 → YDNU-02 when installed |
| 12 | Depth sounder | Depth, water temperature | Via NMEA 2000 → YDNU-02 when installed |

---

## 9.1 Secrets — Emplacement

| Secret | Emplacement | Dans git ? |
|--------|-------------|-----------|
| InfluxDB token | `.env` | ❌ jamais |
| Grafana admin password | `.env` | ❌ jamais |
| OpenClaw token | `.openclaw-token` | ❌ jamais |
| GitHub PAT | Env variable SSH session | ❌ jamais |
| WiFi password | `config/wifi-ap.txt` | ⚠️ git privé seulement |

#

---

## 8. SIGNAL K — SOURCES ET PRIORITÉS (mis à jour 2026-06-15)

> Ces sections sont fusionnées depuis `docs/HARDWARE/INSTRUMENT-INVENTORY.md`.
> Pour la topologie complète du bus N2K et la matrice des flux PGN, voir le fichier canonical :
> 📌 **`docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`**

### 8.1 Inventaire des sources Signal K

| # | Instrument | Modèle | Protocole | Source Signal K | Fréquence | État |
|---|------------|--------|-----------|-----------------|-----------|------|
| 1 | GPS + Cap vrai | Unicore UM982 | NMEA 0183 / USB | `signalk-um982-gnss.UM982-HDG` | 1 Hz | ✅ Actif |
| 2 | IMU | WIT WT901BLECL | Bluetooth LE | `signalk-wit-imu-ble.XX` | 10 Hz | ✅ Actif |
| 3 | Vent masthead | Calypso UP10 | Bluetooth LE | `calypso-up10` (UDP:4123) | 1 Hz | ✅ Actif |
| 4 | Vent masthead (N2K) | B&G WS320 | NMEA 2000 | `nmea2000_ws320` | 5 Hz | ✅ Actif |
| 5 | Gateway N2K | Yacht Devices YDNU-02 | USB / N2K | transparent | N/A | ✅ Actif |
| 6 | Chartplotter | B&G Vulcan 7 FS | NMEA 2000 | `vulcan_internal` | 1 Hz | ✅ Actif |
| 7 | Systèmes RPi | Raspberry Pi 4 | Interne | `signalk-system-stats` | 0.2 Hz | ✅ Actif |
| 8 | Batterie | SOK BMS LiFePO4 | Bluetooth LE | Direct InfluxDB (bypass SK) | 0.2 Hz | ✅ Actif |
| 9 | Baromètre | Yacht Devices YDBC-05 | NMEA 2000 | `nmea2000_ydbc05` | 0.5 Hz | ✅ Actif |
| 10 | Transpondeur AIS | B&G AIS700 Class B | NMEA 2000 | `nmea2000_ais700` | event-driven | ✅ Actif |

### 8.2 Noms des sources Signal K

## Signal K Source Name Reference

| Signal K Source | Instrument | Notes |
|-----------------|------------|-------|
| `signalk-um982-gnss.UM982-HDG` | Unicore UM982 | Proprietary #UNIHEADING sentences — dual-antenna heading. HEADINGOFFSET 90 applied 2026-05-17 |
| `signalk-wit-imu-ble.XX` | WIT WT901BLECL | Hull mount, 30 Hz — primary attitude source (highest SK priority) |
| `nmea2000_ws320` | B&G WS320 | Apparent wind via N2K backbone → YDNU-02 → SK. Also feeds Vulcan 7 directly at 5 Hz |
| `calypso-up10` | Calypso UP10 | Primary SK wind source (BLE → UDP port 4123). Active via systemd service |
| `vulcan_internal` | B&G Vulcan 7 FS | Secondary GPS/COG/SOG from Vulcan internal GNSS |
| `signalk-system-stats` | Raspberry Pi 4 | CPU temp (K), load, RAM |
| `nmea2000_ydbc05` | Yacht Devices YDBC-05 | Atmospheric pressure via N2K → YDNU-02 → SK |
| `nmea2000_ais700` | B&G AIS700 | AIS vessel targets via N2K → YDNU-02 → SK (`vessels.*` namespace) |
| `sok_bms` | SOK Battery BMS | Direct InfluxDB — bypasses Signal K entirely |

---

### 8.3 Priorités de source — Vent
## Wind Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `calypso-up10` | `environment.wind.*` | Primary — masthead BLE sensor, 1 Hz |
| 2 | `nmea2000_ws320` | `environment.wind.*` | Secondary — N2K via YDNU-02, 5 Hz |

> The WS320 also feeds the Vulcan 7 FS **directly** at 5 Hz without going through Signal K
> (N2K backbone shortcut). The Vulcan uses this for real-time sail trim display.

### 8.4 Priorités de source — Attitude
## Attitude Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `signalk-wit-imu-ble.XX` | `navigation.attitude.*` | WIT IMU — 30 Hz. Also feeds PGN 127257 → Vulcan 7 via YDNU-02 |
| 2 | `calypso-up10` | `navigation.attitude.*` | Compass mode only (if `--compass=on`) — overridden by WIT |

---

### 8.5 Non installés
## Not Installed

| # | Instrument | Role | Notes |
|---|------------|------|-------|
| 11 | Speed through water (STW) / loch | Boat speed, leeway | Via NMEA 2000 → YDNU-02 when installed |
| 12 | Depth sounder | Depth, water temperature | Via NMEA 2000 → YDNU-02 when installed |

---

## 9.2 .gitignore — Fichiers exclus

```
.env
*.env
.openclaw-token
*.secret
*.key
*.pem
```

#

---

## 8. SIGNAL K — SOURCES ET PRIORITÉS (mis à jour 2026-06-15)

> Ces sections sont fusionnées depuis `docs/HARDWARE/INSTRUMENT-INVENTORY.md`.
> Pour la topologie complète du bus N2K et la matrice des flux PGN, voir le fichier canonical :
> 📌 **`docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`**

### 8.1 Inventaire des sources Signal K

| # | Instrument | Modèle | Protocole | Source Signal K | Fréquence | État |
|---|------------|--------|-----------|-----------------|-----------|------|
| 1 | GPS + Cap vrai | Unicore UM982 | NMEA 0183 / USB | `signalk-um982-gnss.UM982-HDG` | 1 Hz | ✅ Actif |
| 2 | IMU | WIT WT901BLECL | Bluetooth LE | `signalk-wit-imu-ble.XX` | 10 Hz | ✅ Actif |
| 3 | Vent masthead | Calypso UP10 | Bluetooth LE | `calypso-up10` (UDP:4123) | 1 Hz | ✅ Actif |
| 4 | Vent masthead (N2K) | B&G WS320 | NMEA 2000 | `nmea2000_ws320` | 5 Hz | ✅ Actif |
| 5 | Gateway N2K | Yacht Devices YDNU-02 | USB / N2K | transparent | N/A | ✅ Actif |
| 6 | Chartplotter | B&G Vulcan 7 FS | NMEA 2000 | `vulcan_internal` | 1 Hz | ✅ Actif |
| 7 | Systèmes RPi | Raspberry Pi 4 | Interne | `signalk-system-stats` | 0.2 Hz | ✅ Actif |
| 8 | Batterie | SOK BMS LiFePO4 | Bluetooth LE | Direct InfluxDB (bypass SK) | 0.2 Hz | ✅ Actif |
| 9 | Baromètre | Yacht Devices YDBC-05 | NMEA 2000 | `nmea2000_ydbc05` | 0.5 Hz | ✅ Actif |
| 10 | Transpondeur AIS | B&G AIS700 Class B | NMEA 2000 | `nmea2000_ais700` | event-driven | ✅ Actif |

### 8.2 Noms des sources Signal K

## Signal K Source Name Reference

| Signal K Source | Instrument | Notes |
|-----------------|------------|-------|
| `signalk-um982-gnss.UM982-HDG` | Unicore UM982 | Proprietary #UNIHEADING sentences — dual-antenna heading. HEADINGOFFSET 90 applied 2026-05-17 |
| `signalk-wit-imu-ble.XX` | WIT WT901BLECL | Hull mount, 30 Hz — primary attitude source (highest SK priority) |
| `nmea2000_ws320` | B&G WS320 | Apparent wind via N2K backbone → YDNU-02 → SK. Also feeds Vulcan 7 directly at 5 Hz |
| `calypso-up10` | Calypso UP10 | Primary SK wind source (BLE → UDP port 4123). Active via systemd service |
| `vulcan_internal` | B&G Vulcan 7 FS | Secondary GPS/COG/SOG from Vulcan internal GNSS |
| `signalk-system-stats` | Raspberry Pi 4 | CPU temp (K), load, RAM |
| `nmea2000_ydbc05` | Yacht Devices YDBC-05 | Atmospheric pressure via N2K → YDNU-02 → SK |
| `nmea2000_ais700` | B&G AIS700 | AIS vessel targets via N2K → YDNU-02 → SK (`vessels.*` namespace) |
| `sok_bms` | SOK Battery BMS | Direct InfluxDB — bypasses Signal K entirely |

---

### 8.3 Priorités de source — Vent
## Wind Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `calypso-up10` | `environment.wind.*` | Primary — masthead BLE sensor, 1 Hz |
| 2 | `nmea2000_ws320` | `environment.wind.*` | Secondary — N2K via YDNU-02, 5 Hz |

> The WS320 also feeds the Vulcan 7 FS **directly** at 5 Hz without going through Signal K
> (N2K backbone shortcut). The Vulcan uses this for real-time sail trim display.

### 8.4 Priorités de source — Attitude
## Attitude Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `signalk-wit-imu-ble.XX` | `navigation.attitude.*` | WIT IMU — 30 Hz. Also feeds PGN 127257 → Vulcan 7 via YDNU-02 |
| 2 | `calypso-up10` | `navigation.attitude.*` | Compass mode only (if `--compass=on`) — overridden by WIT |

---

### 8.5 Non installés
## Not Installed

| # | Instrument | Role | Notes |
|---|------------|------|-------|
| 11 | Speed through water (STW) / loch | Boat speed, leeway | Via NMEA 2000 → YDNU-02 when installed |
| 12 | Depth sounder | Depth, water temperature | Via NMEA 2000 → YDNU-02 when installed |

---

## 9.3 Firewall UFW — Ports ouverts

| Port | Service | Accès |
|------|---------|-------|
| 3000 | Signal K | LAN + Cloudflare Tunnel |
| 3001 | Grafana | LAN + Cloudflare Tunnel |
| 8086 | InfluxDB | LAN uniquement |
| 22 | SSH | LAN uniquement |
| 18789 | OpenClaw Gateway | localhost uniquement |

#

---

## 8. SIGNAL K — SOURCES ET PRIORITÉS (mis à jour 2026-06-15)

> Ces sections sont fusionnées depuis `docs/HARDWARE/INSTRUMENT-INVENTORY.md`.
> Pour la topologie complète du bus N2K et la matrice des flux PGN, voir le fichier canonical :
> 📌 **`docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`**

### 8.1 Inventaire des sources Signal K

| # | Instrument | Modèle | Protocole | Source Signal K | Fréquence | État |
|---|------------|--------|-----------|-----------------|-----------|------|
| 1 | GPS + Cap vrai | Unicore UM982 | NMEA 0183 / USB | `signalk-um982-gnss.UM982-HDG` | 1 Hz | ✅ Actif |
| 2 | IMU | WIT WT901BLECL | Bluetooth LE | `signalk-wit-imu-ble.XX` | 10 Hz | ✅ Actif |
| 3 | Vent masthead | Calypso UP10 | Bluetooth LE | `calypso-up10` (UDP:4123) | 1 Hz | ✅ Actif |
| 4 | Vent masthead (N2K) | B&G WS320 | NMEA 2000 | `nmea2000_ws320` | 5 Hz | ✅ Actif |
| 5 | Gateway N2K | Yacht Devices YDNU-02 | USB / N2K | transparent | N/A | ✅ Actif |
| 6 | Chartplotter | B&G Vulcan 7 FS | NMEA 2000 | `vulcan_internal` | 1 Hz | ✅ Actif |
| 7 | Systèmes RPi | Raspberry Pi 4 | Interne | `signalk-system-stats` | 0.2 Hz | ✅ Actif |
| 8 | Batterie | SOK BMS LiFePO4 | Bluetooth LE | Direct InfluxDB (bypass SK) | 0.2 Hz | ✅ Actif |
| 9 | Baromètre | Yacht Devices YDBC-05 | NMEA 2000 | `nmea2000_ydbc05` | 0.5 Hz | ✅ Actif |
| 10 | Transpondeur AIS | B&G AIS700 Class B | NMEA 2000 | `nmea2000_ais700` | event-driven | ✅ Actif |

### 8.2 Noms des sources Signal K

## Signal K Source Name Reference

| Signal K Source | Instrument | Notes |
|-----------------|------------|-------|
| `signalk-um982-gnss.UM982-HDG` | Unicore UM982 | Proprietary #UNIHEADING sentences — dual-antenna heading. HEADINGOFFSET 90 applied 2026-05-17 |
| `signalk-wit-imu-ble.XX` | WIT WT901BLECL | Hull mount, 30 Hz — primary attitude source (highest SK priority) |
| `nmea2000_ws320` | B&G WS320 | Apparent wind via N2K backbone → YDNU-02 → SK. Also feeds Vulcan 7 directly at 5 Hz |
| `calypso-up10` | Calypso UP10 | Primary SK wind source (BLE → UDP port 4123). Active via systemd service |
| `vulcan_internal` | B&G Vulcan 7 FS | Secondary GPS/COG/SOG from Vulcan internal GNSS |
| `signalk-system-stats` | Raspberry Pi 4 | CPU temp (K), load, RAM |
| `nmea2000_ydbc05` | Yacht Devices YDBC-05 | Atmospheric pressure via N2K → YDNU-02 → SK |
| `nmea2000_ais700` | B&G AIS700 | AIS vessel targets via N2K → YDNU-02 → SK (`vessels.*` namespace) |
| `sok_bms` | SOK Battery BMS | Direct InfluxDB — bypasses Signal K entirely |

---

### 8.3 Priorités de source — Vent
## Wind Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `calypso-up10` | `environment.wind.*` | Primary — masthead BLE sensor, 1 Hz |
| 2 | `nmea2000_ws320` | `environment.wind.*` | Secondary — N2K via YDNU-02, 5 Hz |

> The WS320 also feeds the Vulcan 7 FS **directly** at 5 Hz without going through Signal K
> (N2K backbone shortcut). The Vulcan uses this for real-time sail trim display.

### 8.4 Priorités de source — Attitude
## Attitude Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `signalk-wit-imu-ble.XX` | `navigation.attitude.*` | WIT IMU — 30 Hz. Also feeds PGN 127257 → Vulcan 7 via YDNU-02 |
| 2 | `calypso-up10` | `navigation.attitude.*` | Compass mode only (if `--compass=on`) — overridden by WIT |

---

### 8.5 Non installés
## Not Installed

| # | Instrument | Role | Notes |
|---|------------|------|-------|
| 11 | Speed through water (STW) / loch | Boat speed, leeway | Via NMEA 2000 → YDNU-02 when installed |
| 12 | Depth sounder | Depth, water temperature | Via NMEA 2000 → YDNU-02 when installed |

---

## 9.4 YDNU-02 Silent Mode

```bash
# En cas de bug Signal K → protéger le bus N2K
echo YDNU SILENT ON > /dev/ttyACM0
# LED bleue = mode silencieux (lecture seule)
```

---

## 11. PROCÉDURES DE DÉMARRAGE

### 10.1 Démarrage normal (ordre)

```bash
# 1. Signal K (premier — toujours)
sudo systemctl start signalk

# 2. Docker (InfluxDB + Grafana + Regatta)
cd ~/midnightrider-navigation
docker compose up -d

# 3. Services Python BLE
sudo systemctl start calypso_anemometer calypso_watchdog

# 4. Vérification
sudo systemctl status signalk calypso_anemometer
docker compose ps
```

### 10.2 Arrêt propre (ordre inverse)

```bash
sudo systemctl stop calypso_anemometer calypso_watchdog
docker compose down
sudo systemctl stop signalk
```

### 10.3 Vérification rapide pré-régate

```bash
# État des services
sudo systemctl status signalk calypso_anemometer
docker compose ps

# Données live Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/ | \
  jq '{headingTrue, speedOverGround, position: .position.value}'

# Batterie SOK
curl -s http://localhost:3000/signalk/v1/api/vessels/self/ | \
  jq '.electrical' 2>/dev/null || \
  docker exec influxdb influx query \
  'from(bucket:"midnight_rider") |> range(start: -5m) |> filter(fn:(r) => r._measurement == "sok_bms") |> last()'

# Pression atmosphérique
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/outside/pressure | \
  jq '.value / 100 | tostring + " hPa"'
```

---

## 12. JOURNAL DES CHANGEMENTS MAJEURS

| Date | Changement | Impact |
|------|-----------|--------|
| 2026-04-25 | Déploiement initial RPi 4 | Système opérationnel |
| 2026-04-28 | Audit sécurité + rotation tokens | Sécurité renforcée |
| 2026-05-01 | Polaires J/30 v1 (incorrectes) | — |
| 2026-05-12 | SOK BMS integration complète | Monitoring batterie actif |
| 2026-05-13 | Inventaire instruments v1 | Documentation |
| 2026-05-17 | **HEADINGOFFSET 90 permanent (UM982 NVRAM)** | Cap corrigé ✅ |
| 2026-05-17 | **attitude.js patché (PGN 127257 → Vulcan 7)** | Gîte sur Vulcan ✅ |
| 2026-05-19 | YDBC-05 barometer installé sur N2K | Pression active ✅ |
| 2026-05-19 | AIS700 installé sur N2K | AIS actif ✅ |
| 2026-05-20 | Révision complète documentation hardware | Datasheets à jour |
| 2026-05-20 | Polaires J/30 v3 — données ORC réelles (UK) | Polaires corrigées ✅ |
| 2026-05-20 | **Ce document — Architecture v4.0** | Référence canonique |

---

## 13. FICHIERS DE RÉFÉRENCE CLÉS

| Fichier | Rôle |
|---------|------|
| `docs/ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md` | Ancien doc archi (partiellement obsolète) |
| **`docs/ARCHITECTURE-REFERENCE-2026-05-20.md`** | **CE DOCUMENT — référence canonique** |
| `docs/HARDWARE/INSTRUMENT-INVENTORY.md` | Inventaire instruments à jour |
| `docs/DATA-SCHEMA-MASTER.md` | Schéma complet données Signal K / InfluxDB |
| `docs/GRAFANA-UNIT-CONVERSIONS.md` | Conversions unités pour Grafana |
| `docs/SYSTEM-SUMMARY.md` | Résumé système (référencé par Dust) |
| `docs/DASHBOARDS-README.md` | Guide dashboards Grafana (référencé par Dust) |
| `logs/latest.json` | Journal d'exécution OC |
| `data/polars/j30_orc.json` | Polaires J/30 v3 — données ORC réelles |
| `docker-compose.yml` | Configuration Docker (InfluxDB, Grafana, Regatta) |
| `.env` | Secrets (NON versionné) |

---

**Maintenu par :** Denis LAFARGE + OC (OpenClaw via Dust)  
**Prochain événement :** Block Island Race — 2026-05-22  
**Contact urgence :** `logs/latest.json` → état système en temps réel


---

## REPOSITORY CLEANUP & STRUCTURE — 2026-05-29

### Cleanup Rounds Completed

**Round 1 (commit b3aaacf):** Removed 11 debug/superseded files
- Debug logs (3 files)
- Duplicate documentation (2 files)
- Superseded scripts (5 files)
- Old dashboard version (1 file)

**Round 2 (commit aae1073):** Removed 4 files, moved 3 files
- Debug artifacts: ble_diagnostic.txt, diagnostic_raw.txt
- MCP dedup: mcp/racing-server.js, mcp/racing-package.json
- Root reorganization: 3 docs moved to docs/

**Round 3 (commit a1a279e):** Removed 34 files
- docs/grafana-dashboards/ (complete duplicate)
- docs/archive/ (12 abandoned specs)
- logs/ (12 debug artifacts)
- .gitignore: added *.pyc rule

### Repository Structure (Post-Cleanup)

```
midnightrider-navigation/
├── grafana-dashboards/          # Active Grafana dashboard JSONs (13 dashboards)
├── docs/                        # Documentation (architecture, integration, hardware)
│   ├── OPERATIONS/              # Field test, race day checklists
│   ├── HARDWARE/                # Datasheets (Calypso, UM982, WIT, Vulcan, etc.)
│   ├── INTEGRATION/             # Setup guides for each device
│   ├── SOFTWARE/                # Signal K, Grafana, InfluxDB docs
│   └── index.md                 # Documentation index
├── scripts/                     # Deployment & monitoring scripts
├── logs/                        # Operational logs (latest.json, cleanup logs, oc-actions.log)
├── mcp/                         # Model Context Protocol servers (race, weather, polar, etc.)
├── plugins/                     # Signal K plugins (2 versions of astronomical)
├── portal/                      # Web dashboard (HTTP server)
├── regatta/                     # Race-day reporting system
├── data/                        # Polar curves (J30 ORC)
└── docker-compose.yml           # Container orchestration
```

### Known Plugin Duality

**Astronomical Plugin:** Two versions exist in plugins/
- signalk-astronomical.js (11.4 KB)
- signalk-astronomical-direct.js (10.0 KB)

**Status:** Configuration shows `signalk-astronomical.json` enabled with NOAA station 8518750
**Decision:** Keep both versions; unclear which is active. Recommend consolidation in future refactor.

### Pending Issues

1. **logs/__pycache__/write_log.cpython-313.pyc** — Python bytecode file committed (should be in .gitignore)
2. **Astronomical plugin duplication** — Two working versions, unclear which is "primary"

### Cleanup Summary

| Metric | Value |
|--------|-------|
| Total files deleted | 57 |
| Total files moved | 3 |
| Repository size reduction | ~15 KB |
| Cleanup rounds | 3 |
| Status | ✅ COMPLETE |

---
**Cleaned on:** 2026-05-29 22:35 UTC
**Cleaned by:** OC Agent (automated)


---

## Changelog — 2026-06-15 — WIT Acceleration Corrected

**Commits:** 039581b + e052630 + 9fe25f2d

| Bug | Cause | Fix | Result |
|---|---|---|---|
| rateOfTurn = -769°/s (physically impossible) | CMD_ACCEL read register 0x61 (unknown/garbage data) | CMD_ACCEL → register 0x34 (standard WIT AX register) | rateOfTurn = -0.02 rad/s ✅ |
| acceleration x=0, y=0, z=4.79 (wrong orientation) | Register 0x61 does NOT contain acceleration | Same fix as above | \|A\| = 10.0 m/s² ≈ g ✅ |

**WIT Register Map Verified:**
- AX=0x34, AY=0x35, AZ=0x36 (acceleration)
- GX=0x37, GY=0x38, GZ=0x39 (gyro rate)

**Confirmed Values at Dock (2026-06-15 12:02 EDT):**
- Acceleration magnitude: 10.005 m/s² (expected gravity ≈ 9.81 m/s²) ✅
- Rate of turn: -0.02 rad/s (vessel at rest) ✅
- WIT mounted level on companionway ✅

**Logging:** WIT + Calypso raised to INFO level (2026-06-15) — was DEBUG @ 8 msg/sec, now <2 msg/sec production logging.


## ⚠️ NOTE ARCHITECTURALE — 2026-06-15 AUDIT

### Corrections apportées

| Composant | État documentation | État réel | Action |
|---|---|---|---|
| signalk-performance-polars | "Actif" | Config orpheline, jamais installé | ✅ SUPPRIMÉ |
| signalk-sails-management-v2 | "Actif" | Config orpheline, jamais installé | ✅ SUPPRIMÉ |
| sk-to-nmea2000 (npm) | "Émet PGNs N2K" | 7 conversions actives | ✅ Opérationnel |
| Output N2K (SK → Vulcan) | "Actif" | ✅ ACTIF — 7 PGNs transmis | ✅ Production |

### Custom N2K Bridge (dormant — alternative au plugin npm)

Fichier: `plugins/signalk-n2k-bridge.js` (Git repo, inactif). Alternative au plugin npm pour contrôle total via Git. Détails:
- Conversions standard (leeway PGN 128000, courant PGN 129291)
- Conversions B&G propriétaires (PGN 130824)
- Architecture extensible et modulaire



---

## 7. STRUCTURE DES LOGS (depuis 2026-06-15)

| Fichier | Type | Rôle |
|---------|------|------|
| logs/latest.json | JSON | Journal d'exécution OC (Dust coordination) |
| logs/oc-actions.log | Texte | Journal détaillé de toutes les actions OC |
| logs/debug/data-flow.log | Texte | Traçage end-to-end du pipeline |
| logs/debug/aggregate-errors.sh | Script | Agrégation des erreurs |
| logs/debug/error-summary.log | Texte | Résumé des erreurs |
| logs/services/.gitkeep | Marqueur | Maintient le répertoire dans git |

Règles .gitignore:
- Exclus: logs/calypso-*.log, logs/services/*.log, logs/debug/*.log, logs/*.txt
- Gardés: logs/latest.json, logs/oc-actions.log, logs/debug/aggregate-errors.sh

---

## 5.8 Configuration Backup (`config/`)

All RPi system configuration files are backed up in `config/` for disaster recovery.
See **[config/README.md](../config/README.md)** for complete inventory and sync/restore procedures.

**Key files:**

| File | Purpose |
|------|----------|
| `config/grafana-custom.ini` | Grafana: iframe embed + 1s refresh (critical for portal) |
| `config/signalk-to-influxdb2.json` | Plugin P3: SK → InfluxDB (token via env var) |
| `config/signalk/settings-sanitized.json` | Signal K server settings (sanitized) |
| `config/system/avahi-daemon.conf` | mDNS: `midnightrider.local` hostname |
| `config/system/dhcpcd.conf` | Static IP on `eth0` |
| `config/ufw-rules.txt` | Firewall rules reference |

> ⚠️ Port 8888 (portal) not in UFW explicit rules — accessible via WiFi hotspot catch-all (192.168.4.0/24) only.


---

## 5.9 Portal Server (`portal/server.py`)

**Purpose**: Main web interface on port 8888. Serves HTML pages, proxies API calls.

See **[portal/README.md](../portal/README.md)** for full documentation.

| Feature | Detail |
|---------|--------|
| Threading | `ThreadingMixIn` — concurrent requests |
| Logging | `logs/services/portal.log` |
| Security | Path sandbox, shutdown auth |
| Grafana | iframe embed (requires `allow_embedding = true`) |

**Pages**: `/` (dashboard), `/viewer.html` (Grafana), `/reporter` (flash), `/ais/*` (AIS)


## 5.10 MCP Servers
See [mcp/README.md](../mcp/README.md).

---

## 5.8 Plugin Deployment Pattern (CRITICAL — 2026-07-12)

### Architecture Principle: SSOT Source in Repo

Signal K loads plugins from the system directory (`/usr/lib/node_modules/`),
NOT from the git repo. This creates a dual-source problem unless carefully managed.

Rule: plugins/signalk-*.js in the repo is the Single Source of Truth (SSOT).
Always edit plugin files there, then sync to the system using scripts/sync-plugins.sh.

### File Locations

| Location | Purpose | Who edits? |
|----------|---------|------------|
| plugins/signalk-*.js | SSOT source — always edit here | ✅ You |
| /usr/lib/node_modules/signalk-server/node_modules/signalk-*/ | Runtime loaded by SK | ❌ Never directly |

### Sync Procedure

After modifying any plugin file:

```bash
# Recommended
sudo bash scripts/sync-plugins.sh
sudo systemctl restart signalk

# Manual fallback
sudo cp plugins/signalk-PLUGIN.js \
  /usr/lib/node_modules/signalk-server/node_modules/signalk-PLUGIN/signalk-PLUGIN.js
sudo systemctl restart signalk
```

### Active Plugin Inventory (2026-07-12)

| Plugin | Version | Status |
|--------|---------|--------|
| signalk-truewind-calculator | 1.0.4 | ✅ Synced |
| signalk-current-calculator | 1.0.4 | ✅ Synced |
| signalk-j30-leeway | 1.0.4 | ✅ Synced |
| signalk-heading-true-calculator | 1.0.6 | ✅ Synced |

### Outputs of signalk-truewind-calculator (v1.0.4)

Always published (ground-referenced):
- environment.wind.directionTrue
- environment.wind.speedOverGround
- environment.wind.angleTrueGround

Always published (water-referenced):
- environment.wind.angleTrueWater
- environment.wind.speedTrue

> Note: At STW = 0 (dock/unavailable), water-ref output defaults to 0 for speed.
> Angle calculations always work (STW factor is just a magnitude scale).
> Values diverge from ground-ref once the boat is moving through water (STW > 0).
