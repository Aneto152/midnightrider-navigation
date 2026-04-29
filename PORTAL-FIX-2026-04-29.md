# Portal HTTP :8888 Fix — 2026-04-29

## Problème
Portal HTTP :8888 retournait HTTP 404 sur `/viewer.html` après le déplacement des fichiers.

## Cause
Le process `python3 -m http.server 8888` tournait depuis le mauvais répertoire (racine du projet au lieu de `/portal`).

## Solution appliquée
1. Arrêter le process existant: `pkill -f "http.server 8888"`
2. Relancer depuis `/portal`: `cd portal && python3 -m http.server 8888`

## Vérification
```bash
curl http://localhost:8888/viewer.html  # HTTP 200 ✅
curl http://localhost:8888/index.html   # HTTP 200 ✅
```

## Service systemd (optionnel pour persistence)
```bash
sudo cp portal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable portal
sudo systemctl start portal
```

## Status
✅ Portal opérationnel
- http://localhost:8888/viewer.html → HTTP 200
- http://localhost:8888/index.html → HTTP 200
- http://localhost:8888/ → HTTP 200
