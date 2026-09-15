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
