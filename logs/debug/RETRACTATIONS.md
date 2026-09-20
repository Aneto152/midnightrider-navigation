# Retractations - depot public - 2026-09-17

Ce fichier recense les affirmations fausses que j ai fait commiter dans ce
depot, et ce qui est vrai a leur place. Il est tenu en ajout : rien n y est
efface, aucun commit n est reecrit.

## Defaut 55 - verdict FAITS_MANQUANTS errone (H6a)

**Affirme** : la chaine historique ne trouve pas les faits obligatoires
dans InfluxDB (verdict `FAITS_MANQUANTS`).

**Vrai** : les quatre requetes de schema portaient sur 365 jours et ont
leve `TimeoutError`. Le code de la sonde faisait
`except Exception -> manquant.append()`, ce qui a transforme quatre
depassements de delai en quatre absences de donnees. Les faits etaient la.

**Cause** : une absence de signal lue comme un signal d absence.

## Defaut 56 - "la chaine historique n a jamais ete executee" (H6a)

**Affirme** : aucune execution de `mediaman/historical_entrypoint.py`.

**Vrai** : `logs/services/mediaman-historical-entrypoint.log` porte une
execution complete et reussie le 2026-09-15T14:31:05, 370 octets generes,
publication en dry-run verifiee.

**Cause** : j ai deduit l etat du systeme depuis le depot. Le depot n est
pas le systeme.

## Defaut 59 - "1 reponse sur 1 provient d une cible AIS" (H6c)

**Affirme** : dans `logs/debug/contexte-ais-2026-09-17.md`, un taux de
pollution AIS de 1 sur 1, presente comme une mesure.

**Vrai** : 11 sondes sur 12 ont renvoye l etat ERREUR. Le denominateur ne
comptait que les sondes reussies. Le taux reel de pollution est INCONNU.
Le message d erreur etait capture par la sonde puis jamais affiche.

**Ce qui reste vrai** : le defaut 58 lui-meme. Il ne repose pas sur une
statistique mais sur la lecture du fichier (`mcp/servers/racing.js` ne
contient aucun filtre de contexte) et sur une preuve par l exemple : un
rejeu a bien renvoye `vessels.urn:mrn:imo:mmsi:368217460` comme vitesse
"du bateau".

## Defaut 60 - skew "12/12 acceptes en fenetre 60 s" (H6c)

**Affirme** : apres filtrage du contexte, 12 instants sur 12 presentent un
ecart temporel inferieur a la limite de 1000 ms.

**Vrai** : la sonde lisait `rows[0]` d une reponse Flux non groupee. Sans
`group()`, InfluxDB renvoie une ligne PAR SERIE, dans un ordre qui n est
pas chronologique. Trois anomalies du meme rapport en decoulent :

- l etape 3 datait le contexte du bateau au 23 juillet alors que l etape 5
  y lisait des donnees du 7 septembre ;
- le meme instant 13:46 donnait 148 ms en fenetre 60 s et 200441 ms en
  fenetre 300 s, ce qui est impossible avec un `last()` correct ;
- `CONTEXTE_POINTS=21713` comptait une serie parmi plusieurs.

**Conclusion** : le chiffre de skew n est pas etabli. Il devra etre
remesure avec `tools/fluxprobe.py`.

## Remede structurel

`tools/fluxprobe.py` (ce meme commit) est desormais la seule sonde Flux
autorisee. Ses 45 tests verrouillent les trois disciplines dont l absence
a produit les defauts 55, 59 et 60 : quatre etats explicites, interdiction
de lire `rows[0]`, denominateur egal au nombre de tentatives.

## Observation transmise a l autre chantier - non corrigee ici

`tools/influx_powerbi_export/annotated_csv.py`, methode `parse_stream()` :
la branche `if len(row) == len(headers)` n a pas de `else`. Toute ligne
dont la largeur differe de l en-tete est abandonnee sans trace. C est le
meme motif. Ce script n y touche pas : autre perimetre.

## Defaut 92 - un Signal K deduit d une etiquette (H14c)

**Affirme** : `/home/aneto/.openclaw/workspace/docker-compose.yml` declare
un Signal K en conteneur avec `restart: unless-stopped`.

**Vrai** : ce fichier declare `influxdb`, `grafana`, `regatta` et
`start-line-worker`, et aucun Signal K. Il a ete lu par H14b-1 :
`declare un Signal K : non`.

**Cause** : le conteneur orphelin porte dans ses etiquettes
`com.docker.compose.project.config_files` le chemin du compose qui l a
cree en avril. J ai lu cette etiquette et conclu ce que le fichier
declarait aujourd hui, sans jamais l ouvrir. Un chantier a failli le
renommer ; ce qui l a arrete n est pas ma comprehension mais une garde de
prudence portant sur une condition sans rapport.

## Le trou de config/wifi-ap.txt - il n a jamais existe (H14c)

**Affirme** : la barriere `tests/mcp/test_h9b_coherence_doc_code.py`
echouait sur tout clone propre, parce que
`test_tout_chemin_cite_dans_architecture_master_existe` exigeait
l existence de `config/wifi-ap.txt`, fichier volontairement non suivi.
Le message du commit `842c3104` le dit en toutes lettres.

**Vrai** : ce test appelle `_ignore_par_git()`, donc `git check-ignore`,
depuis bien avant H14c, et `wifi-ap.txt` figure dans `.gitignore`. Sur un
clone propre la barriere passe. Verification faite sur le commit
`895ba2c6`, dans un arbre git, sans le fichier : 41 tests, 41 passes.

**Cause** : mon banc d essai travaillait sur une archive `tar.gz` extraite,
sans repertoire `.git`. Hors arbre git, `git check-ignore` ne peut rien
repondre et l echappatoire ne s applique pas. J ai conclu du dispositif
d observation a la chose observee - exactement le motif du defaut 92, le
meme jour.

**Ce qui reste vrai** : les deux detecteurs de chemins absents ne se
comportaient pas pareil. `chemins_morts()` ignorait git. H14d lui donne le
meme recours et retire l exception codee en dur.

## 97 et 98 annonces ouverts, alors que 98 ne l etait pas (H14c)

**Affirme** : le message du commit `3d60635c` et le compte rendu
`logs/debug/premisse-fausse-2026-09-20.md` annoncent l ouverture des
defauts 97 et 98. Le defaut 97 dit que *les quatre* conteneurs de
production sont definis hors depot.

**Vrai** : le chantier n a ouvert que 97, et un seul conteneur sur quatre
est defini hors depot. Sa sortie le dit :
`PROJET_PROPRIETAIRE_DES_CONTENEURS=midnightrider-navigation`,
`DEFAUTS_OUVERTS=25`.

**Cause** : une variable au singulier pour quatre conteneurs. Trois sur
quatre appartenaient au projet du depot, la variable a pris leur valeur,
et la condition d ouverture de 98 est tombee du mauvais cote. Les textes,
eux, etaient ecrits d avance et n ont ete conditionnes a rien.

**Corrige par** : H14d, qui reecrit 97 sur la mesure, ouvre 98, avertit
dans le guide de secours, et exige desormais qu un compte rendu encore
cite par un defaut dise l etat du jour.
