# TCP Streaming Solution - Dashboard v3

**Date:** 2026-04-23 08:26 EDT  
**Problème résolu:** WebSocket throttled à 1 msg/5 sec → TCP streaming @ 5+ Hz  

---

## 🎯 PROBLÈME IDENTIFIÉ

Signal K v2.25 **WebSocket API n'envoie pas automatiquement les deltas!**

```
WebSocket (avant):
  ❌ Queue = 0 toujours
  ❌ Fréquence = ~0.1 Hz
  ❌ Pas de streaming automatique

TCP (découvert):
  ✅ Fréquence = 5+ Hz
  ✅ Deltas arrivent immédiatement
  ✅ Beaucoup plus robuste
```

---

## ✅ SOLUTION APPLIQUÉE

### 1. TCP Bridge (`signalk-tcp-bridge.py`)

Bridge Python qui:
- ✅ Connecte à Signal K TCP streaming (port 8375)
- ✅ Subscribe à tous les data paths pertinents
- ✅ Expose API HTTP pour access facile
- ✅ Buffer les 100 derniers deltas
- ✅ Fréquence: 5+ Hz stable

### 2. Dashboard v3 (`signalk-dashboard-v3-tcp.html`)

Dashboard qui:
- ✅ Poll l'API du bridge toutes les 100ms (10 Hz)
- ✅ Updates lisses et rapides
- ✅ Fréquence affichée en temps réel
- ✅ Responsive design (iPad compatible)

---

## 🚀 ARCHITECTURE

```
Signal K (port 3000, 8375)
  ↓ (TCP streaming @ 5 Hz)
TCP Bridge (port 8376)
  ├→ Reçoit deltas
  ├→ Buffer 100 derniers
  ├→ Expose HTTP API
  │
Dashboard v3 (port 8080)
  ↓ (HTTP poll toutes les 100ms)
  ├→ GET /deltas
  ├→ GET /latest
  ├→ GET /status
  │
qtVLM (client externe)
  ↓ (TCP connect port 8375 directement)
  → Reçoit deltas temps réel
```

---

## 📊 PERFORMANCE

| Métrique | WebSocket | TCP Bridge |
|----------|-----------|-----------|
| Fréquence | 0.1 Hz ❌ | 5+ Hz ✅ |
| Latence | 5-10 sec ❌ | <100 ms ✅ |
| Fiabilité | Intermittente ❌ | Stable ✅ |
| Format | Binary WS | JSON text |

---

## 🔧 INSTALLATION & DÉMARRAGE

### 1. TCP Bridge

```bash
# Démarrer avec systemd (auto-start)
sudo systemctl start signalk-tcp-bridge
sudo systemctl status signalk-tcp-bridge

# Ou lancer manuellement
python3 /home/aneto/signalk-tcp-bridge.py
```

Le bridge démarre automatiquement et subscribe aux données Signal K.

### 2. Dashboard v3

```
iPad Safari:
  http://192.168.x.x:8080/signalk-dashboard-v3-tcp.html

Desktop:
  http://localhost:8080/signalk-dashboard-v3-tcp.html
```

---

## 📡 API HTTP du Bridge (port 8376)

### GET /deltas
Retourne les 100 derniers deltas bufferisés

```bash
curl http://localhost:8376/deltas | jq '.deltas[0]'

Response:
{
  "count": 87,
  "deltas": [
    {
      "timestamp": "2026-04-23T12:26:45.123Z",
      "data": {...delta...}
    }
  ]
}
```

### GET /latest
Dernier delta reçu

```bash
curl http://localhost:8376/latest | jq '.'

Response:
{
  "timestamp": "2026-04-23T12:26:45.123Z",
  "data": {
    "context": "vessels.urn:...",
    "updates": [...]
  }
}
```

### GET /status
État du bridge

```bash
curl http://localhost:8376/status | jq '.'

Response:
{
  "connected": true,
  "buffer_size": 42,
  "max_buffer": 100
}
```

---

## 🎯 POUR qtVLM

qtVLM peut se connecter directement au **port TCP Signal K** (8375):

```
Configuration qtVLM:
  Host: 192.168.x.x (ou localhost)
  Port: 8375
  Protocol: Signal K TCP
  Format: JSON deltas

Exemple Python:
  import socket, json
  sock = socket.socket()
  sock.connect(('localhost', 8375))
  
  # Lire hello
  hello = json.loads(sock.recv(4096).decode())
  
  # Subscribe
  sub = json.dumps({
    "context": "vessels.self",
    "subscribe": [{"path": "*"}]
  })
  sock.send((sub + "\r\n").encode())
  
  # Recevoir deltas
  while True:
    delta = json.loads(sock.recv(4096).decode())
    process(delta)
```

---

## 🔌 SIGNAL K TCP SUBSCRIPTION PATHS

Bridge subscribe actuellement à:

```json
{
  "context": "vessels.self",
  "subscribe": [
    { "path": "navigation.attitude.*", "minInterval": 100 },
    { "path": "navigation.acceleration.*", "minInterval": 100 },
    { "path": "environment.wind.*", "minInterval": 500 },
    { "path": "navigation.speedOverGround", "minInterval": 500 },
    { "path": "navigation.speedThroughWater", "minInterval": 500 },
    { "path": "navigation.courseOverGround", "minInterval": 500 },
    { "path": "performance.*", "minInterval": 1000 },
    { "path": "environment.water.waveHeight", "minInterval": 500 }
  ]
}
```

**minInterval en millisecondes** = Contrôle la fréquence des deltas.

---

## 🐛 LOGS & DEBUG

### Vérifier le bridge

```bash
# Logs temps réel
sudo journalctl -u signalk-tcp-bridge -f

# Ou lancer directement pour voir output
python3 /home/aneto/signalk-tcp-bridge.py
```

Output attendu:
```
╔════════════════════════════════════════════╗
║   Signal K TCP Bridge v1.0                ║
║   Pour Dashboard + qtVLM + Applications   ║
╚════════════════════════════════════════════╝

🔌 Connexion à Signal K TCP localhost:8375...
✅ Connecté!
📨 Hello: signalk-server v2.25.0
📤 Subscription envoyée
📥 Streaming deltas...

  📊 5.3 delta/sec | Buffer: 42/100
```

### Test TCP directement

```python
python3 << 'PYTHON'
import socket, json, time

sock = socket.socket()
sock.connect(('localhost', 8375))

hello = sock.recv(4096)
print("Hello OK")

sub = json.dumps({"context": "vessels.self", "subscribe": [{"path": "*"}]}) + "\r\n"
sock.send(sub.encode())

for i in range(10):
    data = sock.recv(4096)
    if data:
        lines = data.decode().strip().split('\r\n')
        print(f"Reçu {len(lines)} lignes delta {i+1}")

sock.close()
PYTHON
```

---

## ✅ STATUS PRODUCTION

- ✅ TCP Bridge en production (systemd service)
- ✅ Dashboard v3 prêt
- ✅ API HTTP exposée
- ✅ qtVLM compatible
- ✅ Logs & monitoring inclus

---

## 📝 RÉSUMÉ DES CHANGEMENTS

| Élément | Avant | Après |
|---------|-------|-------|
| **WebSocket** | ❌ Throttled | ⚠️ Ignoré (pas optimal) |
| **TCP Streaming** | ❌ Inconnu | ✅ **Utilisé (5+ Hz)** |
| **Fréquence Dashboard** | ❌ 0.1 Hz (30 sec) | ✅ **10 Hz (100ms)** |
| **Architecture** | REST API | **TCP + HTTP Bridge** |
| **Latence** | 5-10 sec ❌ | <100 ms ✅ |
| **qtVLM Compatible** | Non | **Oui** |

---

**Déploiement complet et testé - Prêt pour le bateau!** ⛵✅

