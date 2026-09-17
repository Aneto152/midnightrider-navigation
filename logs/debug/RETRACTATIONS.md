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
