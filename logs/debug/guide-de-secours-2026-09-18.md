# Le guide de secours ne pouvait pas etre suivi

**Chantier** : h12-v1
**Parent** : 4ac4e97c52eb43e5b333ea56b6bde6a9c8ba4b2e
**Commit de contenu** : 6ad1a6b6b24a0d6d81df1a0395f1fde74f77d622

## L audit

`docs/ops/RECOVERY-GUIDE-SAFE.md`, version 1.1 du 2026-04-27, 559 lignes.
Audit mecanique du 2026-09-18 : extraction de tout ce qui ressemble a un
chemin de fichier, puis verification d existence.

| Mesure | Valeur |
|---|---|
| Chemins cites | 53 |
| Existant tels quels | **2** |
| Existant ailleurs dans le depot | 9 |
| Introuvables | 42 |
| Lignes factuellement fausses | 65 |
| Sections touchees | 11 sur 12 |

Le guide decrivait une arborescence `docker/signalk/mcp/` avec sept serveurs
nommes `racing-server.js`, `polar-server.js` et ainsi de suite. Il n existe
aucun repertoire `docker/` dans ce depot ; les serveurs s appellent
`mcp/servers/racing.js`, et il y en a onze. Les trois taches cron listees
pointaient sur des scripts jamais ecrits, alors que l ordonnancement se fait
par quatre timers systemd depuis au moins juillet.

## Le piege actif

STEP 1 du guide, lignes 160 a 172 :

    docker ps | grep -E "influxdb|signalk|grafana"
    cd ${PROJECT_ROOT}/docker/signalk
    docker-compose up -d

`docs/ARCHITECTURE-MASTER.md` ligne 196 : **Signal K, port 3000, systemctl
(JAMAIS docker)**. `SYSTEM-SUMMARY.md` ligne 48 : **systemctl only, NEVER
docker**.

Le document que l on ouvre quand tout va mal apprenait a faire exactement ce
que l architecture interdit, et fournissait la commande pour le faire. Le
conteneur orphelin `signalk`, trouve `Exited (137)` apres quatre mois lors du
diagnostic du 2026-09-18, en est selon toute vraisemblance issu.

Un document de secours faux n est pas equivalent a un document absent. Il est
pire : on le suit precisement dans les moments ou l on n a plus le temps de
verifier ce qu il affirme.

## Ce qui a ete supprime plutot que corrige

Deux sections dupliquaient une source de verite deja juste :

| Section supprimee | Ce qui la remplace |
|---|---|
| Gabarit de configuration Claude, 74 lignes, 7 serveurs | `mcp/claude_desktop_config.example.json`, 12 entrees, exact |
| Carte de l arborescence, 45 lignes, fictive | `docs/INDEX.md` |

Une copie periment plus vite que son original. Un guide de secours qui
duplique deux documents vieillit trois fois plus vite que le systeme qu il
est cense sauver.

## Ce qui a ete etabli par mesure

Aucun chiffre de la version 2.0 n est repris de la version 1.1 :

| Element | Mesure | Source |
|---|---|---|
| Serveurs MCP | 11 | comptage de `mcp/servers/*.js` |
| Outils MCP | 48 | analyse des tableaux `tools[]` |
| Outils de `racing.js` | 2 | idem, conforme a H9 |
| Conteneurs Docker | 4 | `docker-compose.yml` |
| Timers systemd | 4 | `etc/systemd/system/*.timer` |
| Buckets InfluxDB | 1 | releve du 2026-09-18 |

## La barriere, et son propre angle mort

Le premier detecteur ecrit pour cette barriere ne lisait que les chemins
places entre accents inverses. Passe sur la version 1.1, il trouvait **zero**
chemin mort. Il y en avait 62.

Ses angles morts etaient les blocs de code et les arborescences ASCII,
c est-a-dire exactement les endroits ou vivent les commandes qu on execute.
Une barriere qui ne regarde que la prose d un document de procedure ne
regarde pas le document.

Le detecteur retenu lit toutes les lignes. Sur la version 1.1 il releve 62
chemins morts et 20 commandes qui traitent Signal K comme un conteneur ; sur
la version 2.0, rien. Cinq tests nouveaux, dont deux qui interrogent le
detecteur lui-meme sur des echantillons issus de la version 1.1.

## Portee de la garde

Deux documents seulement entrent sous garde :
`docs/ops/RECOVERY-GUIDE-SAFE.md` et
`docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`, qui etait deja propre.

Le recensement complet donne **189 chemins morts** dans la documentation
canonique :

| Document | Chemins morts |
|---|---|
| `docs/INDEX.md` | 119 |
| `docs/ARCHITECTURE-MASTER.md` | 34 |
| `README.md` | 10 |
| `docs/DATA-SCHEMA-MASTER.md` | 9 |
| `mcp/README.md` | 6 |
| `docs/DASHBOARDS-README.md` | 6 |
| `docs/SIGNALK-PLUGINS-INVENTORY.md` | 3 |
| `SYSTEM-SUMMARY.md` | 2 |

Tout mettre sous garde d un coup obligerait a tout corriger dans le meme
passage. Les documents entreront dans la liste a mesure qu ils seront
assainis. `README.md` cite `race-server.js`, `polar-server.js`,
`electrical-server.js` et `imu-server.js` : le meme fantome que le guide, sur
la porte d entree du depot. C est le defaut 82.

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 17 passed in 0.41s ============================== |
| `suite-mcp` | ============================= 85 passed in 39.74s ============================== |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 22.10s ======================= |

## Portee

Aucun service redemarre, aucun conteneur supprime, aucune ecriture InfluxDB,
aucun identifiant lu. Le conteneur orphelin `signalk` n est pas touche par ce
chantier : le supprimer est une action sur l etat du systeme, qui releve du
chantier services et demande une validation.

## Defauts

Fermes : 67 (harnais JS mort, desormais signale comme tel dans le guide),
81 (guide non executable).

Ouverts par ce chantier : 82 (`README.md` cite quatre serveurs fantomes),
83 (189 chemins morts dans la documentation canonique, dont 119 dans
`docs/INDEX.md`).

Restent ouverts : 61, 62, 68, 69, 70, 71, 72, 73, 79 partiel, 80.

## Ce que ce chantier ne prouve pas

Que le guide fonctionne. Il prouve que chaque chemin qu il cite existe et
qu aucune de ses commandes ne contredit la regle du bord. Il ne prouve pas
qu un Raspberry Pi vierge redemarre en le suivant : cette procedure n a
jamais ete repetee sur du materiel. La version 2.0 le dit en toutes lettres
dans sa derniere section, au lieu de promettre 45 minutes comme le faisait la
version 1.1.
