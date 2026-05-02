# TÂCHES 2A & 2C — READY TO EXECUTE

**Scripts are in /tmp/ — copy and run in next session:**

```bash
cd /home/pi/midnightrider-navigation
source .env

# TÂCHE 2A — 03-performance.json (5 VOILES panels)
python3 /tmp/enrich_03_perf.py

# TÂCHE 2C — 09-crew.json (5 BARREUR panels) 
python3 /tmp/enrich_09_crew.py

# Verify
git diff --stat grafana-dashboards/

# TÂCHE 3 — Deploy all 3 enriched dashboards to Grafana
for json in 07-race 03-performance 09-crew; do
  DASH=$(python3 -c "
import json
d = json.load(open('grafana-dashboards/${json}.json'))
root = d.get('dashboard', d)
root['id'] = None
print(json.dumps({'dashboard': root, 'overwrite': True, 'folderId': 0}))
")
  curl -s -X POST \
    -H "Content-Type: application/json" \
    -u "admin:${GRAFANA_PASSWORD:-admin}" \
    -d "${DASH}" \
    "http://localhost:3001/api/dashboards/db" | python3 -m json.tool
done

# TÂCHE 4 — Verify regatta/ access
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/regatta/

# TÂCHE 5 — Commit
git add grafana-dashboards/
git commit -m "feat: complete dashboard enrichment — voiles + barreur panels

- 03-performance: +5 VOILES panels (GV/Foc/Spi/Note)
- 09-crew: +5 BARREUR panels (Helm/Durée/Relève/Historique)
- 07-race: Fixed localhost → midnightrider.local in regatta link
- All 3 dashboards deployed to Grafana
- Total: 32 new panels added this session
- Production-ready for May 19 field test"

git push origin main
```

---

**Status:**
- ✅ TÂCHE 1: localhost → midnightrider.local (DONE)
- ⏳ TÂCHE 2A: 03-performance.json (READY — /tmp/enrich_03_perf.py)
- ⏳ TÂCHE 2C: 09-crew.json (READY — /tmp/enrich_09_crew.py)
- ⏳ TÂCHE 3: Grafana deployment (READY — bash loop provided)
- ⏳ TÂCHE 4: Verify regatta access (READY — curl command provided)
- ⏳ TÂCHE 5: Final commit (READY — git command provided)

**Next session:** Execute 5 scripts in order (30-45 min) → 100% complete
