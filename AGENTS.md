# AGENTS.md — Règles opérationnelles OC (Midnight Rider Navigation)

## ⚠️ RÈGLES ABSOLUES — À lire avant chaque action

### GIT — Règles strictes
- **TOUJOURS** commencer par `git pull origin main` avant tout travail
- **TOUJOURS** committer surround — jamais en detached HEAD
- **TOUJOURS** vérifier après push : `git log --oneline -3` + comparer SHA local vs GitHub
- **JAMAIS** committer sans instruction explicite de Denis
- Si `git status` retourne des commits → tu es en avance, push immédiatement

### RAPPORTS — Ce qui est interdit
- **JAMAIS** écrire "✅ COMPLETE" ou "100% OPERATIONAL" sans avoir vérifié techniquement
- **JAMAIS** inventer un message d'erreur ou une excuse ("sandbox limitation", "RBAC lockdown")
- **JAMAIS** résumer une erreur — copier le message EXACT retourné par la commande
- **JAMAIS** créer un fichier `.md` comme livrable principal d'une tâche technique
- **TOUJOURS** inclure le SHA du dernier commit dans le rapport

### VÉRIFICATIONS OBLIGATOIRES après chaque tâche
- Après déploiement Grafana: vérifier UIDs avec `curl` → HTTP 200
- Après modification portal: vérifier `.env` et service systemd
- Après modification docker-compose: `docker compose ps` + health check
- Après push GitHub: comparer `git log` local vs `git ls-remote origin main`

### RÉPERTOIRES — Ne jamais confondre
- **Répertoire du projet**: `/home/pi/midnightrider-navigation` (= le repo git)
- **Répertoire portal**: `portal/` (relatif au projet root)
- **JAMAIS** servir des fichiers depuis `/home/aneto/.openclaw/workspace/` (OC interne)
- **JAMAIS** utiliser `/home/aneto/` pour des fichiers du projet

### GRAFANA — Règles techniques
- **Datasource UID**: `efifgp8jvgj5sf` (NE JAMAIS `"influxdb"`)
- **Bucket InfluxDB**: `midnight_rider` (NE JAMAIS `"signalk"`)
- **Déploiement**: via provisioning `grafana-provisioning/dashboards/` (pas l'API)
- **Port Grafana**: 3001 (pas 3000)
- **Provisioning path**: `/var/lib/grafana/dashboards`

### PORTAL — Règles techniques
- **Port portal**: 8888
- **Répertoire servi**: `portal/` UNIQUEMENT (via `--directory portal`)
- **NE JAMAIS** exposer `grafana-dashboards/` ou la racine du repo
- **Service systemd**: vérifier ExecStart pointe vers le bon répertoire
- **HTTP Tests**: 
  - `/` → HTTP 200 (index.html)
  - `/.env` → HTTP 404 (bloqué)
  - `/viewer.html` → HTTP 200

### STACK TECHNIQUE — Références

| Service | Port | Accès | Vérification |
|---------|------|-------|--------------|
| Signal K | 3000 | http://localhost:3000 | `curl -s http://localhost:3000/api/` |
| InfluxDB | 8086 | http://localhost:8086 | `curl -s http://localhost:8086/api/v2/ready` |
| Grafana | 3001 | http://localhost:3001 | `curl -s http://localhost:3001/api/health` |
| Portal | 8888 | http://midnightrider.local:8888 | `curl -s http://localhost:8888/` |

### GRAFANA PROVISIONING — Checklist
- ✅ `grafana-provisioning/dashboards/dashboards.yaml` existe
- ✅ `docker-compose.yml` a les 2 volume mounts:
  - `./grafana-provisioning/dashboards:/etc/grafana/provisioning/dashboards`
  - `./grafana-dashboards:/var/lib/grafana/dashboards`
- ✅ Tous les 8 dashboards HTTP 200 au démarrage
- ✅ Aucun déploiement API requis (pas de RBAC issues)

### TIMELINE IMMUABLE

| Date | Événement | Statut |
|------|-----------|--------|
| 2026-05-19 | Field test — système doit être opérationnel | ✅ READY |
| 2026-05-22 | Block Island Race (186nm, Stamford CT) | ✅ READY |
| Équipage | Denis + Anne-Sophie | ORC double-handed |

### MEMORY & SESSION CONTEXT
- **SOUL.md**: Qui tu es (résumé du style)
- **USER.md**: Denis (la personne)
- **HEARTBEAT.md**: Tâches de monitoring périodiques
- **MEMORY.md**: Long-term memory (main session only)
- **memory/*.md**: Daily logs
- **Workspace**: `/home/aneto/.openclaw/workspace` (local) → sync to RPi repo

### DEBUGGING COMMON ISSUES

**Portal shows "Directory listing"**
- Check: `sudo systemctl cat portal | grep ExecStart`
- Should be: `ExecStart=/usr/bin/python3 -m http.server 8888 --directory /path/to/portal`

**Grafana dashboards 404**
- Check: `curl -s http://localhost:3001/api/dashboards/uid/<UID>`
- Verify: provisioning YAML exists + docker-compose volumes mounted
- If missing: `docker compose restart grafana`

**Portal blocks .env**
- Check: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/.env`
- Should be: HTTP 404
- If 200: portal routing is broken

---

**Last Updated**: 2026-05-03  
**Session**: Midnight Rider Navigation System (v1.0-production)  
**Author Guidance**: Denis Lafarge + OC Rules
