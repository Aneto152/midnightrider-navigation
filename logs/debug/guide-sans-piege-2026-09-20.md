# Le guide cesse de prescrire ce que le depot interdit

**Chantier** : h14a-v1
**Base** : de89dcc6c418b9139bb6dc17e77ff68c91567926
**Commit de contenu** : 96b84834d85a3fb4d7fed21964336cdbe79812ea

## Le piege

Le guide de secours v2.0, ecrit le matin meme du 2026-09-20, disait :

```
sudo systemctl enable --now mediaman.timer mediaman-events.timer \
                            midnight-logs-commit.timer midnight-logsync.timer
```

Et `etc/systemd/system/midnight-logsync.service`, depuis le 2026-09-17 :

```
# UNITE RETIREE - NE PAS REINSTALLER, NE PAS REPARER
#   la reparer serait NUISIBLE : son ExecStart tronque sur place tout
#   journal de plus de 900 ko a ses 300 dernieres lignes, sans
#   sauvegarde, et elle ne declare aucun User= donc tournerait en root
```

H12 avait trouve le meme genre de piege dans la v1.1 : un
`docker-compose up -d` pour Signal K, alors que la regle du bord est
`systemctl` uniquement. J ai retire celui-la et j en ai introduit un autre,
de la meme famille, dans le document que je venais de reecrire. **Defaut
89.**

Il y avait un troisieme chemin vers le meme accident : les deux blocs du
README des unites qui copiaient `etc/systemd/system/*` en masse. Ils
reinstallaient l unite desarmee sans que personne ait rien tape de
suspect.

## Ce que le releve du 2026-09-20 a tranche

| Ce que la documentation disait | Ce que la machine montre |
|---|---|
| quatre timers armes | **un** : `midnight-logs-commit.timer` |
| `mediaman.timer`, `mediaman-events.timer` | **pas installes**, `LoadState=not-found` — defaut 90 |
| `midnight-logsync.service` en echec | `disabled`, deliberement, absent des unites en echec |
| unites conformes au depot | **quatre divergent** — defaut 91 |
| `telegraf.service` en echec, cause inconnue | sa configuration reclame un parseur `nmea` que Telegraf ne fournit pas : **il n a jamais demarre une seule fois** — defaut 71 |

## Ce sur quoi je m etais trompe

J avais affirme, le matin meme, que le conteneur `signalk` orphelin venait
le plus probablement du `docker-compose up -d` de la v1.1 du guide.
`docker inspect` dit autre chose :

```
projet      : workspace
fichier     : /home/aneto/.openclaw/workspace/docker-compose.yml
redemarrage : unless-stopped
```

Il vient du workspace d OpenClaw, pas du depot. Et le vrai danger n est pas
le conteneur arrete : c est que ce fichier compose existe toujours et
declare un Signal K en `restart: unless-stopped`. Un `docker compose up`
dans ce repertoire lancerait un second Signal K en concurrence du service
systemd sur le port 3000. **Defaut 92**, hors depot, a traiter en H14b.

## Les 344 Mo de .git

| Chemin | Volume cumule dans l historique |
|---|---|
| `logs/services/wit-ble-direct.log` | **3 104 Mo** |
| `logs/debug/data-flow.log` | 1 824 Mo |
| `logs/services/calypso-direct.log` | 517 Mo |

Ce n est pas `data-flow.log` le premier coupable, contrairement a ce que je
supposais hier. Et `.gitignore` exclut pourtant `logs/services/*.log` : il
n y a qu une facon d y arriver, un `git add -f`, exactement ce que fait
l `ExecStart` de l unite desarmee. Sur 2 411 commits, **1 350** sont des
`logs: auto-update`. **Defaut 93.**

## Ce que ce chantier fait

- le guide ne prescrit plus d armer l unite desarmee, et porte un
  avertissement en bloc cite
- son tableau des timers porte l etat **mesure**, colonne `Installed`
  comprise
- la phrase sur les unites en echec est a jour, avec la cause de l echec de
  Telegraf
- les deux copies en masse du README des unites deviennent une boucle qui
  saute `midnight-logsync`
- deux controles nouveaux, et deux echantillons batis sur les lignes
  reelles du jour, qui doivent rendre rouge

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 36 passed in 0.68s ============================== |
| `suite-mcp` | ============================= 104 passed in 41.25s ============================= |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 22.08s ======================= |

## Portee

Aucun service, aucun conteneur, aucune unite installee, aucune ecriture
InfluxDB. **Ce chantier ne modifie que des fichiers du depot.** Les defauts
90 a 93 sont ouverts, pas traites : ils demandent d agir sur la machine, et
c est H14b.

---
*Ecrit par H14a le 2026-09-20T19:41:38.*
