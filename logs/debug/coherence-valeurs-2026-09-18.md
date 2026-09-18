# La barriere ne voyait pas ce qu elle mesurait

**Chantier** : h11b-v1
**Parent** : d8933d99dc3d8e74fb526aa9b840b088f61b7f50
**Commit de contenu** : 94e6f3f7397f7eef805c3c765aa1bf3a50b21f00

## Ce qui s est passe

H11 a termine sur `BUCKETS_FANTOMES_RESTANTS=0` et a inscrit dans
`logs/oc-actions.log` que le defaut 74 etait ferme. Les deux affirmations
etaient fausses, et elles etaient fausses de la meme facon : la mesure ne
mesurait pas ce que son nom annoncait.

Le compte valait zero parce que les motifs de detection ne savaient pas
regarder aux bons endroits, pas parce que la documentation etait juste.

## Les deux angles morts

| Forme rencontree | Motif de H11 | Vue ? |
|---|---|---|
| `INFLUX_BUCKET=signalk` | INFLUX, DB optionnel, underscore, BUCKET | oui |
| `INFLUXDB_BUCKET=signalk` | idem | oui |
| `INFLUX_DB_BUCKET=signalk` | idem | **non** |
| `INFLUX_ORG=...` | INFLUX, underscore, ORG | oui |
| `org="midnight-rider"` | idem | **non** |

Le premier angle mort tient a un underscore. `INFLUX(?:DB)?_` accepte
`INFLUX_` et `INFLUXDB_`, mais pas `INFLUX_DB_`. Le second tient a une
hypothese jamais enoncee : que l organisation ne serait citee que sous forme
de variable d environnement, alors qu elle apparait aussi comme argument
nomme dans du code Python d exemple.

## Ce qui restait faux

| Fichier | Ligne | Valeur | Corrigee en |
|---|---|---|---|
| `docs/setup/INFLUXDB-CONFIG.md` | 37 | bucket `signalk` | `midnight_rider` |
| `docs/INFLUXDB-AUTH-INTEGRATION.md` | 94, 110, 131, 145, 330, 355 | org `midnight-rider` | `MidnightRider` |

La ligne 37 est la plus parlante : elle se trouve quatre lignes au-dessus de
la ligne 41 que H11 venait de corriger, dans le meme bloc `environment` du
meme fichier `docker-compose.yml` d exemple. Le bloc annoncait donc deux
buckets contradictoires, et la barriere le declarait conforme.

## Le correctif, cote barriere

Les motifs sont elargis a `INFLUX[A-Z_]*BUCKET`, `INFLUX[A-Z_]*ORG`, au
mot-cle nu `org=` et aux options `--bucket` et `--org`. Les valeurs qui
commencent par un signe dollar sont exclues explicitement : elles nomment une
variable, pas un bucket.

Mais l elargissement des motifs n est pas la lecon. La lecon est qu une
barriere qui n examine que le corpus ne peut pas signaler sa propre cecite.
Trois tests nouveaux interrogent donc le detecteur lui-meme : une liste
d echantillons reellement rencontres dans le depot, que chaque motif doit
savoir voir. Ajouter une forme a cette liste avant de la corriger est
desormais la facon d etendre cette barriere.

Executee sur le depot avant correction, la barriere elargie tombe sur
exactement les deux points ci-dessus.

## Une procedure qui cite trois artefacts inexistants

En balayant `docs/setup/INFLUXDB-CONFIG.md`, la section *How to Activate
Cloud* demande de modifier `scripts/astronomical-data.sh`, de redemarrer le
service docker-compose `astronomical`, et renvoie a
`scripts/replicate-to-cloud.sh`. Aucun des trois n existe :
`docker-compose.yml` ne declare que `influxdb`, `grafana`, `regatta` et
`start-line-worker`, et `scripts/` ne contient ni l un ni l autre script.

La section n est pas supprimee : la replication cloud reste un objectif. Elle
recoit une rectification datee en tete, pour qu elle se lise comme une
intention et non comme un mode d emploi. Le seul script de synchronisation
cloud reel du depot est `scripts/post-race-cloud-sync.sh`.

## Champs de tete de latest.json

Les champs `task`, `date` et `status` de `logs/latest.json` annoncaient encore
*MediaMan etape 4E.1* du 2026-09-17, alors que `last_task` disait H11. Le
document de reference se contredisait en son sein. Ils sont remis en
coherence, et le porteront desormais.

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 12 passed in 0.34s ============================== |
| `suite-mcp` | ============================= 80 passed in 39.71s ============================== |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 22.00s ======================= |

## Portee

Aucun service redemarre, aucun conteneur touche, aucune ecriture InfluxDB,
aucun fichier supprime, aucun identifiant lu.

## Defauts

Ouverts : 75 (motif de bucket trop etroit, corrige ici), 76 (motif
d organisation trop etroit, corrige ici), 77 (trois artefacts inexistants
cites dans une procedure, rectifies ici), 78 (champs de tete de latest.json
perimes, corriges ici).

Le defaut 74 est ferme pour de bon, cette fois avec un detecteur dont la
portee est elle-meme testee.

Restent ouverts et sans rapport avec ce chantier : 61, 62, 67, 68, 69, 70,
71, 72, 73.

## Ce que ce chantier ne prouve pas

Que la barriere voit tout. Elle voit les formes de la liste d echantillons,
qui est une liste de ce qui a deja ete rencontre. Une forme d ecriture encore
jamais employee dans le depot passera encore. La difference est qu il existe
maintenant un endroit ou l ajouter, et un test qui echouera si on l ajoute
sans corriger la valeur.
