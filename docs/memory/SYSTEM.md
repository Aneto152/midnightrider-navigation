# 🧠 Système de Mémoire — MidnightRider

## Comment ça marche

Je suis un assistant sans mémoire persistante. Chaque nouvelle session, je redémarre de zéro.

**Pour éviter les trous de mémoire:**
1. **MEMORY.md** dans `/home/aneto/.openclaw/workspace/` — mémoire long-terme de l'assistant
2. **Ce répertoire (`docs/memory/`)** — sauvegarde du GitHub = source de vérité pour le projet
3. **Session transcripts** — passé récent si tu demandes "check memory"

## Flux d'actualisation

### ✅ Ce qui se sauvegarde automatiquement
- Configs Docker & SignalK (git auto-backup chaque nuit à 2h)
- Logs d'alertes et sauvegardes

### ⚠️ Ce qui se perd entre sessions
- Credentials (tokens, passwords) sauf s'ils sont en mémoire MEMORY.md
- Contexte conversationnel récent
- Décisions temporaires

### 🔄 Solution
**À chaque session importante**, j'actualise les fichiers mémoire du GitHub:
```bash
# Exemple
docs/memory/2026-04-19.md  # Notes du jour
docs/memory/CREDENTIALS.md # Tokens (chiffrés ou hachés si public)
docs/memory/ARCHITECTURE.md # Vue d'ensemble système
```

## Fichiers critiques à maintenir

### docs/memory/CREDENTIALS.md
**NE PAS VERSIONNER EN CLAIR!** (Voir `.gitignore`)

- InfluxDB local token: 4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==
- InfluxDB Cloud org: 48a34d6463cef7c9
- InfluxDB Cloud URL: https://us-east-1-1.aws.cloud2.influxdata.com
- InfluxDB Cloud token: **EXPIRÉ** ❌ (À renouveler)
- Grafana admin: admin / MidnightRider
- GitHub token: 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 (à rotation chaque trimestre)

### docs/memory/ARCHITECTURE.md
Vue d'ensemble du système:
- GPS (UM982) → SignalK → InfluxDB (local & cloud) → Grafana
- Instruments: NMEA0183 (GPS), NMEA2000 (YDWG-02), kflex
- Interfaces: SignalK (3000), Grafana (3001), Interface Régate (5000)

### docs/memory/STATUS.md
État actuel du système (à mettre à jour régulièrement):
- Services actifs/inactifs
- Derniers commits
- TODO critiques

## Commande de rappel

Quand tu dis "**Check memory**" ou "**Tu te souviens de...**":

```bash
# Je vais faire ça:
1. memory_search() — cherche dans MEMORY.md + memory/*.md + session transcripts
2. memory_get() — pull les lignes spécifiques
3. Si rien trouvé → "Je vais check le GitHub docs/memory/"
```

## Anti-amnésie checklist

✅ Avant de partir:
- [ ] Commit & push GitHub toutes les configs modifiées
- [ ] Actualiser docs/memory/STATUS.md
- [ ] Documenter les décisions dans docs/memory/YYYY-MM-DD.md

✅ À chaque nouvelle session:
- [ ] `memory_search` → check long-terme
- [ ] Check GitHub `docs/memory/` si besoin context complet

✅ Todos/décisions importantes:
- [ ] Ajouter à docs/memory/TODO.md dans le repo
- [ ] Ajouter à MEMORY.md dans workspace (pour moi)

---

**TL;DR:** GitHub + MEMORY.md = pas d'amnésie. Je vais chercher là avant de dire "j'sais pas".
