# WebSocket Streaming - Diagnostic Systématique

**Date:** 2026-04-23 08:18 EDT  
**Pour:** Denis Lafarge  
**Sujet:** Queue size = 0 mais refresh très lent - Lister et tester les hypothèses  

---

## 🎯 SYMPTÔMES OBSERVÉS

```
✅ Queue size en dashboard: TOUJOURS 0
✅ Updatecount: Très bas (0.1-1 Hz)
❌ Taux de refresh: Extrêmement faible (30 sec)
```

**Le fait que queue = 0 est important!** Ça signifie que les messages N'ARRIVENT PAS du serveur, pas un problème de traitement côté client.

---

## 📋 HYPOTHÈSES À TESTER (Classées par probabilité)

### **H1: Signal K ne stream PAS les données (Probabilité: 🔴 TRÈS ÉLEVÉE)**

Le problème vient du **serveur**, pas du client!

**Symptômes:**
- Queue = 0 (pas de messages reçus)
- Update count très bas
- Toutes les valeurs affichent "--"

**Cause possible:**
- Signal K utilise une autre configuration
- Les plugins n'envoient pas de données
- Subscribe parameter incorrect
- Signal K throttle actif même en WebSocket

**Test #1 - WebSocket brut:**
```bash
# Test direct du WebSocket Signal K
wscat -c "ws://localhost:3000/signalk/v1/stream?subscribe=self"

# Attends les messages
# Dois voir: ~10 messages/sec
# Ou: Rien du tout (confirme H1)
```

---

### **H2: Dashboard ne se connecte PAS au bon serveur**

**Symptômes:**
- Localhost resolved différent sur iPad
- Dashboard essaie de se connecter à iPad au lieu du bateau

**Cause possible:**
- window.location.hostname = IP iPad, pas IP bateau
- CORS/cross-origin blocking

**Test #2 - Console navigateur:**
```javascript
// Ouvre console (F12) et tape:
console.log(window.location.hostname)
console.log(ws.url)

// Doit afficher:
// "localhost" ou "192.168.x.x" (l'IP du bateau)
```

---

### **H3: Signal K version < 2.25 n'a pas le streaming WebSocket**

**Symptômes:**
- WebSocket répond mais n'envoie que le hello, puis silence

**Cause possible:**
- Version trop ancienne
- Feature désactivée

**Test #3 - Vérifier version Signal K:**
```bash
curl -s http://localhost:3000/signalk | jq '.server.version'

# Doit retourner: "2.25.0" ou plus récent
```

---

### **H4: Plugin WIT n'envoie PAS de données (Peut-être éteint?)**

**Symptômes:**
- WebSocket connecté MAIS pas de deltas
- Dashboard reçoit "hello" mais rien après

**Cause possible:**
- Plugin disabled dans settings.json
- Plugin crashé
- Plugin pas activé manuellement via Admin UI

**Test #4 - Vérifier plugin actif:**
```bash
# Check config
curl -s http://localhost:3000/skServer/plugins | jq '.[] | select(.id=="signalk-wit-imu-usb")'

# Doit afficher: running = true, enabled = true
```

---

### **H5: Throttling différent pour WebSocket (Signal K core setting)**

**Symptômes:**
- WebSocket actif mais throttled
- UPDATE_INTERVAL réglé bas

**Cause possible:**
- Setting dans Signal K: updateInterval=30000ms (30 sec!)
- Ou autre throttle au niveau du serveur

**Test #5 - Vérifier settings Signal K:**
```bash
# Lire settings.json
cat /home/aneto/.signalk/settings.json | jq '.updateInterval'

# Doit afficher: 100 ou similar (en ms)
# Si 30000 = PROBLÈME TROUVÉ!
```

---

### **H6: Navigateur Safari bloque WebSocket (iPad spécifique)**

**Symptômes:**
- Fonctionne sur desktop
- Ne fonctionne pas sur iPad Safari

**Cause possible:**
- Safari privacy settings
- Mixed HTTP/HTTPS
- WebSocket blocked

**Test #6 - Test depuis desktop vs iPad:**
```bash
# Depuis desktop: curl test
curl -v "http://localhost:8080/"

# Depuis iPad: Ouvre Dashboard
# Compare le taux d'update
```

---

### **H7: Server HTTP rate-limiting ou caching**

**Symptômes:**
- HTTP 304 (Not Modified) responses
- Cache headers preventing WebSocket init

**Cause possible:**
- Dashboard server (port 8080) cache HTML agressif
- Node.js keep-alive timeout

**Test #7 - Vérifier headers:**
```bash
curl -v http://localhost:8080/

# Cherche:
# Cache-Control: no-cache, no-store (bon)
# ou
# Cache-Control: max-age=3600 (mauvais!)
```

---

## 🧪 PLAN D'ACTION - Tester dans cet ordre:

### **ÉTAPE 1: Vérifier que Signal K envoie réellement des données (H1)**

```bash
# Test WebSocket direct (pas de dashboard)
wscat -c "ws://localhost:3000/signalk/v1/stream?subscribe=self"

# Attends 10 secondes
# Dois voir environ 10 messages (@ 1 Hz minimum)
# Ou RIEN (confirme H1)
```

**Résultat attendu:**
```
{"name":"...","version":"..."}
{"context":"...","updates":[...]}
{"context":"...","updates":[...]}
...
```

**Si RIEN:**
→ Problème Signal K, pas dashboard. Go H3/H4/H5.

**Si messages arrivent:**
→ Signal K fonctionne. Go H2.

---

### **ÉTAPE 2: Vérifier que Dashboard se connecte au bon serveur (H2)**

```bash
# Dans Dashboard, ouvre console (F12) et tape:
window.location.hostname
ws.url

# Doit afficher l'IP correcte du bateau
```

**Si localhost vs 192.168.x.x incorrect:**
→ Dashboard se connecte au mauvais endroit. Fix H2.

---

### **ÉTAPE 3: Vérifier version Signal K (H3)**

```bash
curl -s http://localhost:3000/signalk | jq '.server.version'

# Doit afficher: "2.25.0" ou newer
```

**Si < 2.25:**
→ Version trop vieille. Go H5 (upgrade peut-être?).

---

### **ÉTAPE 4: Vérifier plugin WIT (H4)**

```bash
# Check if plugin is enabled
curl -s http://localhost:3000/skServer/plugins | \
  jq '.[] | select(.id=="signalk-wit-imu-usb") | {running, enabled}'

# Doit afficher: {"running":true,"enabled":true}
```

**Si enabled=false:**
→ Plugin pas activé. Ouvre Admin UI et active-le.

**Si running=false:**
→ Plugin peut-être planté. Redémarre Signal K.

---

### **ÉTAPE 5: Vérifier updateInterval Signal K (H5)**

```bash
cat /home/aneto/.signalk/settings.json | jq '.updateInterval'

# Doit afficher: 100 (ms) ou moins
# Si 30000 ou plus = C'EST ÇA!
```

**Si updateInterval=30000:**
→ TROUVÉ! Change à 100:

```bash
# Edit settings.json
nano /home/aneto/.signalk/settings.json

# Change:
# "updateInterval": 30000,
# À:
# "updateInterval": 100,

# Redémarre Signal K
sudo systemctl restart signalk
```

---

### **ÉTAPE 6: Tester sur Desktop vs iPad (H6)**

```bash
# Depuis desktop:
curl http://localhost:8080/

# Depuis iPad Safari:
http://192.168.x.x:8080

# Compare le taux d'update (updates/sec)
```

**Si différent:**
→ Problème Safari. Essaye différent navigateur (Chrome).

---

### **ÉTAPE 7: Vérifier Cache headers (H7)**

```bash
curl -v http://localhost:8080/ 2>&1 | grep -i "cache"

# Doit afficher: 
# Cache-Control: no-cache, no-store, must-revalidate
```

**Si autre:**
→ Ajouter headers au serveur HTTP.

---

## 🎯 RÉSUMÉ: QUE TESTER IMMÉDIATEMENT?

**Test #1: WebSocket brut (PRIORITÉ 🔴)**

```bash
# Installation wscat si besoin:
npm install -g wscat

# Test:
wscat -c "ws://localhost:3000/signalk/v1/stream?subscribe=self"

# Attends 5 secondes
```

**Résultat:**
- ✅ Messages arrivent toutes les secondes → Signal K OK, problème client (H2/H6/H7)
- ❌ Rien du tout → Problème Signal K (H1/H3/H4/H5)

---

## 📊 TABLEAU DE DÉCISION

```
Queue = 0 toujours
     ↓
     ├→ Test WebSocket brut
     │  ├→ Messages arrivent (10/sec)
     │  │  └→ Problème CLIENT (H2/H6/H7)
     │  │     └→ Check: hostname, cache, Safari
     │  │
     │  └→ Rien reçu
     │     └→ Problème SERVEUR (H1/H3/H4/H5)
     │        └→ Check: version, plugin, updateInterval
     │
     └→ Si toujours bloqué
        └→ Logs Signal K:
           sudo journalctl -u signalk -n 50 --no-pager
```

---

## 📚 DOCUMENTATION SIGNAL K PERTINENTE

Source: https://signalk.org/specification/1.5.0/doc/streaming_api.html

**Points clés:**
1. WebSocket DOIT envoyer "hello" d'abord
2. Puis envoyer "delta" messages en continu
3. Pas de throttle spécifié dans la spec
4. Query parameters: `subscribe=self|all|none`
5. `sendCachedValues=true|false` (défaut: true)

---

## 🚀 PROCHAINES ÉTAPES IMMÉDIATEMENT

1. **Teste wscat** (Test #1 ci-dessus)
2. **Partage le résultat** (arrivent des messages? Combien?)
3. **Selon résultat**, on identifie la bonne hypothèse
4. **On teste l'hypothèse** spécifiquement
5. **On applique le fix**

---

**Important:** Le fait que `queue = 0` est une BONNE CHOSE - ça signifie que le problème est clairement identifié: Signal K n'envoie pas de données (ou très lentement).

Fais le test #1 (wscat) et dis-moi **exactement** ce que tu vois!

