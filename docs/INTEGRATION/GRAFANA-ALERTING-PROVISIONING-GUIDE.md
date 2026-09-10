# Grafana Alert Provisioning Guide: Structure and Validation

**Document Version:** 1.0  
**Last Updated:** 2026-09-10  
**Scope:** Grafana alert rule provisioning for Midnight Rider Navigation  
**Applies to:** Grafana 12.3.1 and later

---

## 1. Purpose and Scope

This guide documents the correct structure and validation requirements for alert rule provisioning in Grafana 12.3.1. It is intended to:

- Prevent provisioning failures due to schema mismatches
- Ensure all alert rules are validated and deployed successfully
- Provide rollback procedures for safe recovery from configuration errors
- Establish best practices for maintaining alert provisioning files

**This guide is a procedure and reference only—it does not implement runtime configuration changes.**

---

## 2. Grafana Version Context

**Affected Version:** Grafana 12.3.1

**Key Change:** Grafana 12.3.1 enforces stricter validation of alert rule provisioning files. It requires:

- Explicit `relativeTimeRange` declarations on query data entries
- Folder names that do not conflict with built-in Grafana folders
- Valid time range specifications for all alert queries

**Consequence of non-compliance:** Alert provisioning fails, Grafana enters a restart loop, and the container exits with code 1.

---

## 3. Alert Rule Structure

### 3.1 Complete YAML Structure

Alert rules in the provisioning file follow this structure:

```yaml
apiVersion: 1
groups:
  - orgId: 1
    name: alert-group-name
    folder: Alert Folder Name           # Custom folder name (see Folder Provisioning Rules)
    interval: 1m
    rules:
      - uid: example-rule-uid
        title: "Example Alert Title"
        condition: B                     # Reference to the condition expression
        data:
          - refId: A
            datasourceUid: example-datasource-id
            relativeTimeRange:           # CRITICAL: Must be inside data[*], not at rule root
              from: 120                  # Integer seconds; e.g., 120 for 2 minutes
              to: 0                      # Must be <= from
            model:
              refId: A
              # Query model content (e.g., Flux query for InfluxDB)
          - refId: B
            datasourceUid: '-100'        # Expression datasource
            relativeTimeRange:           # Must match the query time window
              from: 120
              to: 0
            model:
              type: threshold
              refId: B
              expression: A
              conditions:
                - evaluator:
                    params: [threshold_value]
                    type: gt
                  operator:
                    type: and
                  query:
                    params: [A]
                  reducer:
                    params: []
                    type: last
                  type: query
        noDataState: OK                 # Alert behavior when no data
        execErrState: Error             # Alert behavior on query error
        for: 30s                        # Duration before alert fires
        annotations:
          description: "Alert description"
          category: "Category name"
        labels:
          severity: critical
          category: "Category name"
```

### 3.2 Critical Placement Rule

**THE `relativeTimeRange` FIELD MUST BE PLACED UNDER THE RELEVANT DATA[*] QUERY ENTRY, NOT AT THE RULE ROOT.**

**INCORRECT (WRONG):**
```yaml
- uid: example-rule
  condition: B
  relativeTimeRange:           # ❌ WRONG: At rule level
    from: 120
    to: 0
  data:
    - refId: A
      datasourceUid: ...
```

**CORRECT (RIGHT):**
```yaml
- uid: example-rule
  data:
    - refId: A
      relativeTimeRange:       # ✅ CORRECT: Under data[*]
        from: 120
        to: 0
      datasourceUid: ...
```

Grafana 12.3.1 validates that `relativeTimeRange` is present under the query entry. If the field is missing or misplaced, Grafana defaults to `[From: 0s, To: 0s]`, which is invalid and causes provisioning to fail.

---

## 4. Folder Provisioning Rules

### 4.1 Folder Declaration

Every provisioning group must declare a folder:

```yaml
groups:
  - name: midnight-rider-alerts
    folder: Midnight Rider Alerts      # Custom folder for alert rules
    interval: 1m
    rules:
      - ...
```

### 4.2 Built-in Folder Conflict

**Critical Rule:** Grafana has a built-in folder named `General`. Do NOT attempt to provision a folder named `General` as a new folder.

**Why:** Grafana's built-in `General` folder already exists and cannot be recreated. Attempting to do so results in the error:

```
A folder with that name already exists
```

**Solution:** Use a descriptive custom folder name that does not conflict with built-in Grafana folders. Examples:

- `Midnight Rider Alerts`
- `Safety Alerts`
- `Performance Alerts`

### 4.3 Folder UID

If a folder UID is explicitly defined, preserve it during any future modifications. Do not change folder UIDs unless explicitly authorized.

### 4.4 Database Integrity

Never delete or modify Grafana's built-in `General` folder through the database. Use the UI only for custom folder management, and use provisioning files for alert rule deployment.

---

## 5. Relative Time Range Rules

### 5.1 Time Range Mapping

Alert queries must specify their time window using Flux `range()` expressions in the query itself, AND declare the equivalent duration in the `relativeTimeRange` field for provisioning validation.

**Standard Mappings:**

| Flux Expression | Duration | from (seconds) | to (seconds) |
|---|---|---|---|
| `range(start:-1m)` | 1 minute | 60 | 0 |
| `range(start:-2m)` | 2 minutes | 120 | 0 |
| `range(start:-3m)` | 3 minutes | 180 | 0 |
| `range(start:-5m)` | 5 minutes | 300 | 0 |

### 5.2 Value Format

- **Type:** Integer (seconds), not strings
- **Example:** `from: 120` (not `from: "120"` or `from: "120s"`)
- **Reason:** Grafana's provisioning schema expects integer seconds for the `from` and `to` fields

### 5.3 Constraint: to ≤ from

The `to` value must never exceed the `from` value:

```yaml
relativeTimeRange:
  from: 120    # 2 minutes in past
  to: 0        # now (0 offset)
```

This constraint ensures that the time range is valid (past → present, not present → future).

### 5.4 Invalid Default Range

If `relativeTimeRange` is missing or misplaced, Grafana defaults to:

```
[From: 0s, To: 0s]
```

This default is **invalid** and will cause the following error:

```
Invalid alert rule query A: invalid relative time range [From: 0s, To: 0s]
```

This indicates a placement error, not a value error. The fix is to move the field to the correct location under the data[*] entry.

---

## 6. Validation Checklist

Before deploying any alert provisioning changes, perform these **read-only verification checks**:

### 6.1 YAML Structure Verification

- [ ] File is valid YAML (parses without syntax errors)
- [ ] All alert rules have a `uid` field
- [ ] All alert rules have a `condition` field pointing to a valid data entry
- [ ] All alert rules have a `data` array with at least 2 entries (A = query, B = condition)

### 6.2 Query Entry Verification

- [ ] Every rule has at least one data entry with `refId: A`
- [ ] The `refId: A` entry has a valid `datasourceUid`
- [ ] The `refId: A` entry contains a query (e.g., Flux for InfluxDB)

### 6.3 Relative Time Range Verification

- [ ] Every `refId: A` entry has a `relativeTimeRange` block
- [ ] The `relativeTimeRange` is **under the data[*] entry, NOT at rule root**
- [ ] Every `relativeTimeRange` has both `from` and `to` fields
- [ ] All `from` and `to` values are integers (seconds)
- [ ] All `to` values are ≤ corresponding `from` values
- [ ] No rule has a `relativeTimeRange` at the rule root level

### 6.4 Query Time Window Verification

For each rule, verify that the Flux query's `range(start:...)` matches the declared `relativeTimeRange`:

- [ ] Flux `range(start:-1m)` → `from: 60`
- [ ] Flux `range(start:-2m)` → `from: 120`
- [ ] Flux `range(start:-3m)` → `from: 180`
- [ ] Flux `range(start:-5m)` → `from: 300`

### 6.5 Folder Verification

- [ ] The `folder` field is declared at the group level (not per-rule)
- [ ] The folder name is NOT `General`
- [ ] The folder name is descriptive and consistent across the file

### 6.6 Grafana Log Verification

After restarting Grafana, check the startup logs for these success indicators:

```
logger=provisioning.alerting msg="starting to provision alerting"
logger=provisioning.alerting msg="finished to provision alerting"
```

Verify that the following errors are NOT present:

- ❌ `A folder with that name already exists` (folder conflict)
- ❌ `Invalid alert rule query A: invalid relative time range [From: 0s, To: 0s]` (placement error)
- ❌ `Failed to provision alerting` (generic provisioning failure)

### 6.7 Container State Verification

- [ ] Grafana container is **Running** (not Restarting)
- [ ] Restart count is **stable** (not incrementing)
- [ ] Exit code is **0** (clean startup)
- [ ] OOMKilled is **false**
- [ ] Container uptime is increasing (no restart loop)

---

## 7. Rollback Guidance

### 7.1 Before Making Changes

Always follow this safety procedure before modifying the provisioning file:

1. **Record the original file hash:**
   ```bash
   sha256sum /home/aneto/midnightrider-navigation/grafana-provisioning/alerting/midnight-rider-rules.yaml
   ```

2. **Create a rollback copy** (without exposing credentials):
   ```bash
   cp /home/aneto/midnightrider-navigation/grafana-provisioning/alerting/midnight-rider-rules.yaml \
      /home/aneto/midnightrider-navigation/grafana-provisioning/alerting/midnight-rider-rules.yaml.backup
   ```

3. **Verify the copy was created:**
   ```bash
   sha256sum /home/aneto/midnightrider-navigation/grafana-provisioning/alerting/midnight-rider-rules.yaml.backup
   ```

### 7.2 Making Targeted Changes

- Modify **only** the intended provisioning file
- Do NOT modify unrelated files (Docker Compose, Signal K, etc.)
- Do NOT modify Grafana's database directly
- Do NOT rebuild Docker images

### 7.3 Restart Grafana

After changes, restart Grafana using the Docker-managed mechanism **only**:

```bash
docker stop grafana
docker start grafana
```

Do NOT use `docker-compose up`, systemctl, or any other restart method.

### 7.4 Verify Startup

Wait 60+ seconds for Grafana to fully stabilize, then check:

```bash
docker inspect grafana --format 'status={{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} restarts={{.RestartCount}}'
docker logs --timestamps --tail 150 grafana 2>&1 | grep -E "(provisioning|alert|error)" | tail -20
```

Expected output:
- `status=running exit=0 oom=false restarts=<stable_number>`
- Logs show: `"finished to provision alerting"`

### 7.5 Rollback If Provisioning Fails

If Grafana enters a restart loop (exit=1, restart count increasing):

1. **Stop Grafana immediately:**
   ```bash
   docker stop grafana
   ```

2. **Restore the backup:**
   ```bash
   cp /home/aneto/midnightrider-navigation/grafana-provisioning/alerting/midnight-rider-rules.yaml.backup \
      /home/aneto/midnightrider-navigation/grafana-provisioning/alerting/midnight-rider-rules.yaml
   ```

3. **Verify the restoration:**
   ```bash
   sha256sum /home/aneto/midnightrider-navigation/grafana-provisioning/alerting/midnight-rider-rules.yaml
   ```

4. **Restart Grafana:**
   ```bash
   docker start grafana
   ```

5. **Verify recovery:**
   ```bash
   docker inspect grafana --format 'status={{.State.Status}} exit={{.State.ExitCode}}'
   ```

### 7.6 Do NOT

- ❌ Delete the Grafana database to fix provisioning errors
- ❌ Rebuild the entire Docker stack for a YAML structure issue
- ❌ Modify Grafana's built-in folders via database queries
- ❌ Use `docker-compose down && docker-compose up` (full stack restart)

---

## 8. Security Requirements

### 8.1 Credential Handling

**Critical Rule:** Never include credentials in the provisioning file.

- Do NOT include datasource URLs with embedded credentials
- Do NOT include API tokens or authentication headers
- Do NOT include hardcoded private IP addresses (use hostnames like `midnightrider.local`)
- Do NOT include MMSI, coordinates, or other operational identifiers

### 8.2 Datasource Configuration

Datasources should be configured through Grafana's datasource provisioning file, **not** in the alert rules file.

Example of WRONG (DO NOT DO):
```yaml
datasourceUrl: "http://user:password@<influxdb-host>:8086"  # ❌ WRONG
```

Example of RIGHT (DO THIS):
```yaml
datasourceUid: efifgp8jvgj5sf  # Reference by UID only
# Actual datasource config is in datasources/datasources.yaml
```

### 8.3 Log Security

- Do NOT display datasource URLs in logs
- Do NOT include tokens or credentials in debug output
- Do NOT expose API keys in error messages

---

## 9. Troubleshooting Symptoms and Causes

### 9.1 Symptom: Grafana in Restart Loop

**Logs show:**
```
Invalid alert rule query A: invalid relative time range [From: 0s, To: 0s]
```

**Possible Causes:**

| Cause | Evidence | Fix |
|---|---|---|
| `relativeTimeRange` at rule root (WRONG) | Field appears before `data:` in YAML | Move field to data[*] entry |
| `relativeTimeRange` missing entirely | No field in data[*] entry | Add field with correct `from` value |
| `relativeTimeRange` with string value | `from: "120"` instead of `from: 120` | Change to integer format |
| `relativeTimeRange` with reversed range | `from: 0, to: 120` (from < to) | Swap values: `from: 120, to: 0` |
| Time window mismatch | Flux `range(start:-2m)` but `from: 60` | Update `from` to match Flux expression |

**Verification:**
```bash
# Check if relativeTimeRange is at rule level (WRONG)
grep -n "^    relativeTimeRange:" midnight-rider-rules.yaml

# Check if relativeTimeRange is under data[*] (RIGHT)
grep -n "      relativeTimeRange:" midnight-rider-rules.yaml
```

### 9.2 Symptom: Folder Conflict Error

**Logs show:**
```
A folder with that name already exists
```

**Cause:** Provisioning file attempts to create the built-in `General` folder.

**Fix:** Change `folder: General` to a custom name like `folder: Midnight Rider Alerts`.

### 9.3 Symptom: Provisioning Timeout

**Logs show:**
```
Failed to provision alerting
```

**Possible Causes:**

- InfluxDB datasource is unreachable
- Grafana database is locked
- Docker volume mount is not synced

**Fix:**
1. Verify InfluxDB is running
2. Verify Docker volume mounts are active
3. Check Grafana error logs for datasource connection errors

### 9.4 Symptom: Alert Rules Not Appearing in UI

**Probable Cause:** Provisioning succeeded (exit=0), but rules not visible in Grafana UI.

**Fix:**
1. Verify the folder name matches what's declared in the provisioning file
2. Verify the alert rule UIDs are unique
3. Manually navigate to the folder in Grafana UI to verify presence

---

## 10. Related Documentation

- Grafana Official Docs: [Alert Rule Provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/manage-alert-rules/)
- InfluxDB Flux Docs: [range() Function](https://docs.influxdata.com/flux/latest/stdlib/universe/range/)
- Midnight Rider Documentation: [System Summary](../../SYSTEM-SUMMARY.md)
- Service Logging Guide: [Service Logging Locations](../../SERVICE-LOGGING-LOCATIONS.md)

---

## Version History

| Date | Version | Change |
|---|---|---|
| 2026-09-10 | 1.0 | Initial guide documenting Grafana 12.3.1 alert provisioning schema and relativeTimeRange placement rules |

---

**End of Document**
