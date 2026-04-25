# TODO — MidnightRider (priorité décroissante)

## 🔴 CRITIQUE

- [ ] **Renouveler token InfluxDB Cloud** (expiré — 401 Unauthorized)
- [ ] **Configurer synchro local → cloud** (plugin SignalK ou script InfluxDB)
  - Source: InfluxDB local (bucket: signalk)
  - Destination: InfluxDB Cloud (org: 48a34d6463cef7c9)
  - Test: Vérifier que Grafana Cloud voit les données

## 🟡 IMPORTANT (avant prochaine régate)

- [ ] Finaliser interface Régate (http://192.168.4.1:5000)
  - [ ] Longueur ligne de départ + angle vs vent réel (nécessite girouette)
  - [ ] Service systemd pour persistance
  - [ ] Test avec iPad en bateau

- [ ] Instruments manquants:
  - [ ] Loch/Sondeur (NMEA2000)
  - [ ] Girouette anémomètre (TWD/TWS → SignalK)
  - [ ] Baromètre (pression)
  - [ ] AIS receiver

- [ ] Alertes vocales (niveau 2-3):
  - [ ] Setup enceinte Bluetooth
  - [ ] Intégration avec SignalK → audio
  - [ ] Timer départ (J-5/3/1/30s/10s)

## 🟢 SOUHAITABLE (post-régate)

- [ ] Dashboard Grafana Cloud pour analyse post-régate
- [ ] Calcul vecteur courant (SOG/COG - STW/HDG)
- [ ] Alertes niveau 3 (complexes):
  - [ ] Divergence méteo
  - [ ] Opportunité spi
  - [ ] Correction mer agitée
  - [ ] Layline optimale

- [ ] Documentation complète en FR
- [ ] Sauvegarde journalière log sécurité

---

## Dernière mise à jour
- **2026-04-19 15:58** — Vérif GPS/InfluxDB OK ✅, Cloud à setup
