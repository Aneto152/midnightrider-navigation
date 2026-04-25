# Stack navigation MidnightRider

Stack Docker pour le J/30 — SignalK + InfluxDB + Grafana.

## Services

| Service   | Port host | Port container | Description                  |
|-----------|-----------|----------------|------------------------------|
| InfluxDB  | 8086      | 8086           | Séries temporelles           |
| Grafana   | 3001      | 3000           | Dashboards                   |
| SignalK   | 3000      | 3000 (host)    | Hub instruments (network_mode: host) |

## Migration depuis natif

### Étape 1 — Migrer les données InfluxDB

```bash
# Arrêter influxdb natif
sudo systemctl stop influxdb

# Copier les données dans le volume Docker
sudo docker run --rm \
  -v influxdb-data:/var/lib/influxdb2 \
  -v /var/lib/influxdb:/var/lib/influxdb \
  influxdb:2.8 \
  cp -r /var/lib/influxdb/. /var/lib/influxdb2/
```

### Étape 2 — Migrer les données Grafana

```bash
sudo systemctl stop grafana-server

sudo docker run --rm \
  -v grafana-data:/var/lib/grafana \
  -v /var/lib/grafana:/var/lib/grafana-native \
  grafana/grafana:12.3.1 \
  cp -r /var/lib/grafana-native/. /var/lib/grafana/
```

### Étape 3 — Migrer la config SignalK

```bash
sudo systemctl stop signalk

sudo docker run --rm \
  -v signalk-data:/home/node/.signalk \
  -v /home/aneto/.signalk:/home/aneto/.signalk-native \
  signalk/signalk-server \
  cp -r /home/aneto/.signalk-native/. /home/node/.signalk/
```

### Étape 4 — Mettre à jour la config SignalK → InfluxDB

Après migration, l'URL InfluxDB dans le plugin `signalk-to-influxdb2` doit pointer vers :
- `http://influxdb:8086` (si SignalK passe en bridge) 
- ou rester `http://localhost:8086` (SignalK en network_mode: host)

⚠️ Avec `network_mode: host`, `localhost` fonctionne toujours → pas de changement nécessaire.

### Étape 5 — Démarrer la stack Docker

```bash
cd /home/aneto/docker/signalk
docker compose up -d
```

### Étape 6 — Désactiver les services natifs

Une fois que tout fonctionne :

```bash
sudo systemctl disable signalk influxdb grafana-server
```

## Backup

```bash
# Backup InfluxDB (à lancer régulièrement ou via cron)
docker exec influxdb influx backup /tmp/backup
docker cp influxdb:/tmp/backup ./backups/influxdb-$(date +%Y%m%d)
```

## Restauration après crash RPi

```bash
cd /home/aneto/docker/signalk
docker compose pull
docker compose up -d
```

C'est tout. 🎉
