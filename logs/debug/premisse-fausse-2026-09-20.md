# La premisse etait fausse

**Chantier** : h14c-v1
**Base** : 895ba2c686a8eb0cdc554599388efcbb1bc6a48b
**Commit de contenu** : 842c310454d763db5854bcaefe694839fb8b7931

## Ce que j avais ecrit

> 92 - /home/aneto/.openclaw/workspace/docker-compose.yml declare un
> Signal K en conteneur avec restart: unless-stopped. C est de la que
> vient le conteneur orphelin. Un docker compose up dans ce repertoire
> lancerait un second Signal K en concurrence du service systemd sur le
> port 3000.

## Ce que le fichier contient

```
services declares : influxdb, grafana, regatta, start-line-worker
declare un Signal K : non
```

Les quatre conteneurs de production du bateau. J ai deduit le contenu de
ce fichier d une **etiquette de conteneur** : le Signal K orphelin porte
dans ses labels `com.docker.compose.project.config_files` le chemin du
compose qui l a cree en avril. Cette etiquette dit d ou vient le
conteneur, pas ce que le fichier declare aujourd hui. Je ne l ai jamais
ouvert - il est hors depot, je n y ai pas acces depuis Dust.

Le chantier H14b-1 proposait de **renommer ce fichier**. Ce qui l a
arrete n est pas ma comprehension : c est une garde posee par prudence,
sur une condition sans rapport avec la vraie raison - un conteneur du
projet tournait. La bonne decision est venue d une precaution, pas d un
raisonnement juste.

## Le compte de la semaine

Treizieme fois qu une mesure est plus etroite que son nom, et la premiere
ou l ecart se paie en geste et non en chiffre :

| # | Ou | Disait | Mesurait |
|---|---|---|---|
| 11 | ma verification du 20/09 | les chemins cites existent | resolus depuis la racine, pas depuis `docs/` |
| 12 | la barriere | tout chemin cite existe | existe **sur cette machine-ci** |
| 13 | **le defaut 92** | ce fichier declare un Signal K | **une etiquette de conteneur le mentionne** |

## Ce que ce chantier repare

- le defaut **92** est retracte, avec la lecture du fichier en preuve
- le paragraphe 2 du constat de H14b-1 est rectifie : il affirmait au
  passe une sauvegarde, un renommage et un `LIRE-MOI` qui n ont jamais eu
  lieu, parce que son texte n etait pas conditionne au statut
- le message du commit de journal `895ba2c6` annonce lui aussi un compose
  retire. Il est faux. On ne reecrit pas l historique : la correction est
  ici et dans le journal des defauts
- **71** est ferme : rendu caduc par 95, telegraf est masque
- **96** est ferme comme doublon de **69**, ouvert le meme jour par un
  chantier qui n avait pas relu la liste des defauts ouverts
- **97** est ouvert : les quatre conteneurs de production sont definis
  hors depot, et le depot porte une seconde definition des memes services
- **98** est ouvert si le projet proprietaire n est pas celui du depot

## La mesure nouvelle

H13 a exige une preuve pour chaque fermeture. Rien n exigeait rien pour
les ouvertures - et c est une ouverture qui a failli coûter cher. Un
defaut ouvert doit desormais porter `| constat:` et dire d ou il sort.

- defauts ouverts : **25**, dont **20** sans constat
- plafond pose a **20** : ce nombre ne peut plus monter
- les chemins cites dans un constat doivent exister, comme ceux des
  preuves de H13

## Ce qui a ete observe, et comment

| Defaut | Observe par |
|---|---|
| 69 | `docker ps -a`, `docker inspect` du conteneur `b03f2697b87c` |
| 90 | `systemctl list-unit-files`, `systemctl show` : `LoadState=not-found` |
| 91 | comparaison des unites installees avec `etc/systemd/system/` |
| 93 | `git cat-file` sur tout l historique, `git count-objects -v` |
| 97 | labels `com.docker.compose.project` des quatre conteneurs, et comparaison caviardee des deux fichiers compose |
| 98 | `container_name` du compose du depot, deja pris par le projet `midnightrider-navigation` |

## Le trou de config/wifi-ap.txt

La barriere echouait sur **tout clone propre** : elle exige que les
chemins cites par `ARCHITECTURE-MASTER` existent, et ce document cite le
fichier du mot de passe WiFi, qu il declare lui-meme *git prive
seulement*. Elle s appelait *tout chemin cite existe* et verifiait
*existe sur cette machine-ci*. Le chemin rejoint les faux amis connus.

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 44 passed in 0.75s ============================== |
| `suite-mcp` | ============================= 112 passed in 40.27s ============================= |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 22.27s ======================= |

## Portee

Aucun geste sur la machine. Lecture seule : `docker inspect`, la
comparaison caviardee des deux compose, `docker compose config`. Aucun
service, aucun conteneur, aucune image, aucune ecriture InfluxDB.

---
*Ecrit par H14c le 2026-09-20T21:21:38.*
