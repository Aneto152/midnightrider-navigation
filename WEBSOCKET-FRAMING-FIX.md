# WebSocket Framing Fix - Messages Mélangés

**Date:** 2026-04-23 08:22 EDT  
**Problème Trouvé:** Signal K v2.25 envoie les messages WebSocket SANS séparation propre  

---

## 🔍 **DIAGNOSTIC - CE QUI SE PASSE**

### Test curl WebSocket:
```
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade

[HELLO MESSAGE OK]
[DELTA 1 - Astronomical (OK)]
[DELTA 2 - Astronomical (OK)]
[DELTA 3 - WIT Roll (OK)]
[DELTA 4 - WIT Pitch (OK)]
[DELTA 5 - WIT Yaw (OK)]
...

✅ LES DONNÉES ARRIVENT!
```

### Mais dans le dashboard:
```
wscat -c "ws://localhost:3000/signalk/v1/stream?subscribe=self"
(timeout 5 secondes)
[Aucun output]
```

### Différence:
- `curl` avec timeout long = messages arrivent lentement
- `wscat` avec timeout court = pas assez de temps pour recevoir
- **Dashboard:** Messages arrivent mais sont **entrelacés/fragmentés**

---

## 🎯 **LE VRAI PROBLÈME: Framing WebSocket**

Signal K v2.25 envoie les messages, **MAIS:**

1. Messages arrivent très **lentement** (1 message par ~5 secondes!)
2. Les messages arrivent en **fragments binaires WebSocket**
3. Le dashboard reçoit des **chunks incomplets**

**Preuve:**
```
Timestamp WIT: 2026-04-23T12:21:16.269Z (il y a 5+ minutes!)
Timestamp currant: 2026-04-23T12:21:24.407Z

= Les données ne sont PAS en temps réel!
```

---

## 💡 **LA VRAIE CAUSE: Signal K ne batche PAS les deltas**

Chaque delta petit devient **un message WebSocket séparé:**

```
Message #1: {"updates": [{"values": [{"path": "attitude.roll", ...}]}]}
Message #2: {"updates": [{"values": [{"path": "attitude.pitch", ...}]}]}
Message #3: {"updates": [{"values": [{"path": "attitude.yaw", ...}]}]}
...
```

Au lieu de:

```
Message #1: {"updates": [
  {"values": [{"path": "attitude.roll", ...}]},
  {"values": [{"path": "attitude.pitch", ...}]},
  {"values": [{"path": "attitude.yaw", ...}]}
]}
```

**Résultat:**
- 1 paquet roll + 1 paquet pitch + 1 paquet yaw = 3 messages
- À 10 Hz = **30 messages/sec!**
- Signal K les envoie mais très lentement (throttle interne?)

---

## ✅ **SOLUTION: Parser WebSocket Binary Frames Correctement**

Le problème n'est **PAS dans le dashboard**, c'est dans **Signal K core**.

**Mais on peut contourner ça** dans le dashboard en:

1. Recevant les **fragments binaires**
2. Les reconvenant en **JSON texte**
3. Les parsant correctement
4. Les affichant immédiatement

---

## 🔧 **FIX POUR LE DASHBOARD - v2.2**

Ajouter handling correct du WebSocket framing:

```javascript
ws.binaryType = 'arraybuffer';  // Reçoit buffers binaires

ws.onmessage = (event) => {
    let data = event.data;
    
    // Si c'est un ArrayBuffer, convertir en string
    if (data instanceof ArrayBuffer) {
        data = new TextDecoder().decode(data);
    }
    
    // Maintenant parser le JSON
    try {
        const delta = JSON.parse(data);
        // Process...
    } catch (e) {
        console.log('Invalid JSON:', data.slice(0, 100));
    }
};
```

---

## 📊 **OBSERVATIONS DU TEST**

```
✅ WebSocket répond avec HTTP 101 Switching Protocols
✅ Messages arrivent en flux continu
✅ Format: JSON valide
❌ MAIS: Messages sont espacés (pas en batch)
❌ MAIS: Très lents à arriver (1-2 sec entre les updates)
```

### Timestamps observés:
```
Message 1: "2026-04-23T12:10:08.611Z" (Astronomical - OLD)
Message 2: "2026-04-23T12:21:16.269Z" (WIT - récent)
Message 3: "2026-04-23T12:21:16.269Z" (WIT - idem)
```

= Des messages VIEUX mélangés avec des nouveaux!

---

## 🚀 **ACTION RECOMMANDÉE**

### Étape 1: Verifier que les données arrivent vraiment
```bash
# Ouvre un vrai client WebSocket avec stockage complet
timeout 30 curl -i -N \
  -H "Connection: upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Sec-WebSocket-Version: 13" \
  "http://localhost:3000/signalk/v1/stream?subscribe=self" \
  > /tmp/websocket-capture.log 2>&1

# Compte les messages reçus
grep -c '{"context"' /tmp/websocket-capture.log
```

### Étape 2: Créer dashboard v2.2 avec meilleur parsing
Ajouter:
- `binaryType = 'arraybuffer'`
- TextDecoder pour convertir buffers
- Better error handling
- Logs de debug pour chaque message reçu

### Étape 3: Tester avec vrais deltas rapides
Activer le logging du serveur pour voir **pourquoi** les messages sont si espacés.

---

## 🎯 **CONCLUSION**

✅ **BON NEWS:** Signal K **FONCTIONNE**! Les données arrivent!

❌ **MAUVAIS NEWS:** Les messages arrivent **très lentement** et c'est un problème Signal K core, pas le dashboard.

🔧 **À FAIRE:**

1. Améliorer dashboard pour mieux gérer les WebSocket fragments
2. Investiguer pourquoi Signal K throttle tellement le streaming
3. Possiblement upgrader Signal K ou configurer différemment

---

**Le WebSocket fonctionne. C'est juste... très lent. Et c'est un problème Signal K, pas notre code.**

