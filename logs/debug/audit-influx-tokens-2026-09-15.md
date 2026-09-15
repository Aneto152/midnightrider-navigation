# InfluxDB token audit — 2026-09-15 — read-only

Produced by audit-h1-influx-tokens.sh (h1-v1) at 20260915T195851Z.
Nothing was modified, restarted or revoked. **No token value appears in
this report**: every token is reduced to sha256[:16]. The exposed token is
identified by the fingerprint `e80a47801529a25c` published in the
SEC-2026-09-14-01 incident record.

## Authorizations

| # | id | description | user | status | scope | sha256[:16] | identified as |
|---|----|-------------|------|--------|-------|-------------|---------------|

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

==============================================================
```

## Ingestion state

```
  signalk is-enabled: enabled

--- newest point in the bucket, single query over the last 30 days ---
  HTTP 200
  newest navigation.position timestamp: 2026-09-07T14:36:24.298Z

--- recent Signal K write errors, if any (masked) ---

==============================================================
```

## Exposure in tracked files

```
  docs/guides/RESTORE.md                               tracked=True  exact-token occurrences=0  token-shaped runs=1  bytes=4171

  .gitignore coverage:
    logs/debug/crash-capture       ABSENT
    logs/diagnostic_raw            ABSENT
    .env                           present
    .openclaw-token                present

==============================================================
```

## Next step, to be validated by Denis

Revocation order remains create -> wire -> verify -> revoke. This audit
exists to establish, before any revocation, which consumer would lose
access, and whether Signal K ingestion is alive at all.
