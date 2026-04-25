# 🔐 SECURITY — InfluxDB Token Regeneration (STEP A)

**Status:** Ancien token compromis (en clair sur GitHub). Nouvelle régénération requise.

---

## ÉTAPE 1: Vérifier que l'ancien token est révoqué

⚠️ **CRITIQUE:** L'ancien token a été exposé publiquement sur GitHub.

```
Ancien token: 4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==
```

Vous DEVEZ révoquer ce token immédiatement dans InfluxDB.

---

## ÉTAPE 2: Générer nouveau token (LOCAL)

### Option A: Via Docker (si conteneur InfluxDB actif)

```bash
# Démarrer les conteneurs si nécessaire
docker-compose up -d influxdb

# Créer nouveau token
docker exec influxdb influx auth create \
  --org MidnightRider \
  --all-access \
  --description "MidnightRider-$(date +%Y%m%d_%H%M%S)" \
  --user <admin-user>

# Sauvegarder le nouveau token généré
# Exemple output:
# ID                    Description                          Token
# 0c7e5a3b8c9d2e1f     MidnightRider-20260425_112000       eyJh...Kj2w==
```

### Option B: Via InfluxDB Admin UI (Web)

```
1. Ouvrir: http://localhost:8086
2. Aller à: Admin → Tokens
3. Click: "Generate Token" → "All Access"
4. Nommer: "MidnightRider-YYYYMMDD"
5. Copier le token généré
```

### Option C: Via InfluxDB CLI (si installé sur RPi)

```bash
influx auth create \
  --org MidnightRider \
  --all-access \
  --description "MidnightRider-$(date +%Y%m%d)"
```

---

## ÉTAPE 3: Sauvegarder le nouveau token LOCALEMENT

```bash
# Créer le fichier .env local (NOT in git)
cat > /home/aneto/.openclaw/workspace/.env << 'EOF'
INFLUX_TOKEN=<PASTE-NEW-TOKEN-HERE>
INFLUX_ORG=MidnightRider
INFLUX_BUCKET=signalk
INFLUX_URL=http://localhost:8086

SIGNALK_URL=http://localhost:3000
SIGNALK_PORT=3000
GRAFANA_URL=http://localhost:3001
GRAFANA_ADMIN_PASSWORD=admin

DEBUG=false
LOG_LEVEL=info
EOF

# Vérifier (ne montre pas le token, par sécurité)
echo "✅ .env créé"
ls -la .env
```

---

## ÉTAPE 4: Charger variables d'environnement

```bash
# Source le fichier .env
source /home/aneto/.openclaw/workspace/.env

# Vérifier
echo $INFLUX_TOKEN  # Doit afficher le nouveau token

# Pour Docker, faire passer les env vars:
docker-compose --env-file .env up -d influxdb
```

---

## ÉTAPE 5: Révoquer l'ANCIEN token dans InfluxDB

Une fois le nouveau token généré et actif:

```bash
# Via Docker
docker exec influxdb influx auth delete \
  --id <OLD-TOKEN-ID>

# Ou via Web UI:
# Admin → Tokens → Find old token → Delete
```

---

## ÉTAPE 6: Vérifier le nouveau token fonctionne

```bash
# Tester connexion InfluxDB
curl -X GET "http://localhost:8086/api/v2/buckets" \
  -H "Authorization: Token $INFLUX_TOKEN" \
  -H "Content-Type: application/json"

# Doit retourner liste des buckets (200 OK)
# Si 401 Unauthorized → token invalide ou expiré
```

---

## ÉTAPE 7: Push des changements à GitHub

Une fois le nouveau token sécurisé LOCALEMENT:

```bash
cd /home/aneto/.openclaw/workspace

# Vérifier que .env n'est PAS commité
git status | grep ".env"  # Ne doit rien montrer

# Push les changements (tokens remplacés par variables)
git push origin main

# GitHub maintenant a:
# ❌ Ancien token: SUPPRIMÉ du repo (remplacé par variables)
# ✅ Nouveau token: JAMAIS commité (stocké localement dans .env)
```

---

## ✅ CHECKLIST FINAL

- [ ] Ancien token révoqué dans InfluxDB
- [ ] Nouveau token généré
- [ ] Nouveau token dans .env local (NOT in git)
- [ ] .env testée (curl fonctionne)
- [ ] Git push complété
- [ ] docker-compose --env-file .env up -d (teste démarrage)

---

## 🔐 SECURITY SUMMARY

**Avant (COMPROMIS):**
```
❌ Token en clair dans 17 fichiers GitHub
❌ Public sur internet
❌ Peut être utilisé par attaquants
```

**Après (SÉCURISÉ):**
```
✅ Tokens remplacés par variables ${INFLUX_TOKEN}
✅ Nouveau token stocké LOCALEMENT dans .env (gitignored)
✅ Aucun secret en dur dans le code
✅ Changement facile de token (éditer .env seulement)
```

---

**⏱️ TEMPS ESTIMÉ:** 5-10 minutes

**🔑 Token nouveau:** À générer par tes soins (je n'ai pas accès direct à InfluxDB)

---

*Document généré: 2026-04-25 11:21 EDT*
