# InfluxDB token audit — 2026-09-15 — read-only

Produced by audit-h1-influx-tokens.sh (h1b-v2) at 20260915T201600Z.
Nothing was modified, restarted or revoked. **No token value appears in
this report**: every token is reduced to sha256[:16]. The exposed token is
identified by the fingerprint `e80a47801529a25c` published in the
SEC-2026-09-14-01 incident record.

## Authorizations

CLI output shape: JSON array

| # | id | description | user | status | scope | sha256[:16] | identified as |
|---|----|-------------|------|--------|-------|-------------|---------------|
| 1 | 10a80277d9d8f000 | admin's Token | admin | active | read+write on /annotations,/authorizations,/buckets | 0cdf3fba24268e7c |  |
| 2 | 10a814629358f000 |  | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | e80a47801529a25c | EXPOSED TOKEN - to revoke |
| 3 | 10b39179ec7d7000 | Grafana-20260512 | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | 2e6fb92a0a7b5705 |  |
| 4 | 10b3917ec6bd7000 | Grafana-20260512-1822 | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | 2f897643ebd9779c |  |
| 5 | 10b3929b4f7d7000 | Grafana-fresh-1778624825 | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | 083a8f304fbb406b |  |
| 6 | 10b3a34816b62000 | start-line-worker-2026-05-12-auto | admin | active | read+write on buckets/bfe67dc473be4e24 | b17d861fa166a4b3 |  |
| 7 | 10b48c80ddb62000 | MidnightRider-Token-2026-05-13-rec | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | c479e01cc819217c |  |
| 8 | 115577aebd73c000 | midnightrider-services 2026-09-15  | admin | active | read+write on buckets/bfe67dc473be4e24 | 3e83dfafb0f92009 | MediaMan .env token - keep |

authorizations listed: 8

## Consumers

```
    configuration.influxes.[0].token               len=88 sha256[:16]=e80a47801529a25c  <<< THE EXPOSED TOKEN IS STILL IN USE HERE

--- container environment variables (names and fingerprints only) ---
  grafana                INFLUX_TOKEN                       EMPTY
  influxdb               no sensitive variable in its environment
  regatta                GPG_KEY                            len=40 sha256[:16]=02978be54c8be7cd
  start-line-worker      INFLUX_TOKEN                       len=88 sha256[:16]=b17d861fa166a4b3
  start-line-worker      INFLUXDB_TOKEN                     len=88 sha256[:16]=25ec316112f46bd6
  start-line-worker      GPG_KEY                            len=40 sha256[:16]=02978be54c8be7cd

--- systemd units carrying an Environment= secret ---

== STEP 2b - ADDED 1 : WHICH TOKEN DOES THE GRAFANA DATASOURCE USE ?
--- provisioning files inside the container (read-only) ---
  datasource-influxdb.yaml
  bytes collected: 357
  provisioning files contain no token-shaped value

--- grafana.db datasource table (copy read locally, never committed) ---
  id=5 name='InfluxDB' type=influxdb url=http://localhost:8086 secure_blob_bytes=88 basic_auth_user=''

  secure_json_data is AES-encrypted with the Grafana secret key, so the
  token CANNOT be fingerprinted from here. If a datasource of type
  influxdb carries a non-empty secure blob, assume it may hold the
  exposed token and verify empirically after rewiring: reload one
  dashboard and check that it still returns data.

```

## Ingestion state

```
  signalk is-enabled: enabled

--- newest point in the bucket, single query over the last 30 days ---
  HTTP 200
  newest navigation.position timestamp: 2026-09-07T14:36:24.298Z

--- ADDED 2 : why is ingestion silent ? (read-only) ---
  data-flow.log last modified : 2026-09-07 10:36:27.336363926 -0400
  last recorded event         :
    [2026-09-07T14:36:27.337Z] [FLOW] Wind→SK: TWD=325.6deg TWS=9.6kts TWA=-101.3deg [signalk-truewind-calculator]
  serial devices present      :
  Signal K self position timestamp (value never printed):
    no answer from the Signal K REST API

--- recent Signal K write errors, if any (masked) ---

```

## Exposure in tracked files

```
  docs/guides/RESTORE.md                               tracked=True  exact-token occurrences=0  token-shaped runs=1  bytes=4171

  .gitignore coverage:
    logs/debug/crash-capture       ABSENT
    logs/diagnostic_raw            ABSENT
    .env                           present
    .openclaw-token                present

```

## Next step, to be validated by Denis

Revocation order remains create -> wire -> verify -> revoke. This audit
exists to establish, before any revocation, which consumer would lose
access, and whether Signal K ingestion is alive at all.

## Rotation 1 — Signal K plugin — 20260915T202511Z

The signalk-to-influxdb2 plugin no longer uses the exposed token.

- new authorization id: `1155af07b7b3c000`
- new token fingerprint: `5c13b0b9efee7017` (value never printed, never committed)
- scope: read+write on bucket `midnight_rider` (`bfe67dc473be4e24`) only, instead of the previous
  organisation-wide scope
- proven before rewiring: one point written to measurement
  `selftest.token_rotation` (HTTP 204) and read back (HTTP 200)
- Signal K restarted with systemctl, is-active=active
- exposed authorization `10a814629358f000`: **still active**, revocation is
  step H3, after the Grafana datasource is handled

Honest limit: no instrument is connected and the data flow stopped on
2026-09-07, so the end-to-end write path cannot be observed today.


## Repair — Grafana token wiring — 20260915T212534Z

The Grafana InfluxDB datasource held **no secret at all**: the API reported
`secure fields set: (none)` and its health endpoint answered
`ERROR`. The dashboards had therefore stopped reading InfluxDB.

Root cause, read in the repository and not guessed:
`grafana-provisioning/datasources/datasource-influxdb.yaml` declares the
datasource with `token: ${INFLUX_TOKEN}`, `docker-compose.yml` forwards
`INFLUX_TOKEN=${INFLUX_TOKEN}` to the container, and that variable was
EMPTY in the running container. Because provisioning is re-applied at every
Grafana start, a fix through the Grafana API would have been erased at the
next restart. The durable fix is to give the container a non-empty value,
then recreate it.

- container recreated with `up -d --no-deps --force-recreate grafana`
  (project `midnightrider-navigation`); influxdb, regatta and start-line-worker verified to be
  the exact same containers before and after
- token handed to the container: the one already in `.env`, fingerprint
  `3e83dfafb0f92009`; observed in the new container: `3e83dfafb0f92009`
- **accepted trade-off**: that authorization is bucket-scoped but carries a
  write permission, while Grafana only ever needs to read. Hardening it to
  least privilege is one line of `docker-compose.yml` plus one new token,
  deliberately postponed.
- datasource `efifgp8jvgj5sf` secure fields after: token
- health: ERROR -> OK
- bounded 60 s probe: 3 row(s) read directly from InfluxDB, 0
0 row(s)
  through the Grafana proxy (HTTP 400)
- dashboards listed by Grafana: 20 before, 20 after
- verdict: **REPAIRED**
- authorizations created: 0, revoked: 0

Two side facts recorded for H3: the read-only authorization
`1155b5f81bb3c000`, created by the aborted first attempt, is orphaned and
should be revoked; and `logs/debug/crash-capture-2026-06-28T190455Z.log`
and `logs/diagnostic_raw.txt` still contain the exposed token, which an
earlier version of this report failed to list.

Honest limits: no dashboard panel was rendered by this step. Only the
datasource health endpoint and one bounded query were exercised, and the
data window is the last one the boat produced, on 2026-09-07.

**Security finding**: the Grafana API still accepts its default admin
password, and `GF_AUTH_ANONYMOUS_ENABLED=true`. Out of scope here, H3.

