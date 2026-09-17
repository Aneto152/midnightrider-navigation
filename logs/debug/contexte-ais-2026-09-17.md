# Défaut 58 — `racing.js` ne filtre pas le contexte — 2026-09-17

Lecture seule. Aucun code de production, aucun service, aucune unité,
aucun conteneur n'a été modifié.

## Le défaut

`mcp/servers/racing.js` ligne 322 construit, pour chacun des quatre faits
obligatoires :

```flux
from(bucket: "...")
  |> range(start: <as_of - window>, stop: <as_of>)
  |> filter(fn: (r) => r._measurement == "navigation.position")
  |> filter(fn: (r) => r._field == "lat")
  |> keep(columns: ["_time", "_value"])
  |> group()
  |> sort(columns: ["_time"])
  |> last(column: "_time")
```

Il n'y a **aucun filtre de contexte**. Le bucket `midnight_rider` ne contient
pas seulement la position du Midnight Rider : il contient aussi celle de chaque
cible AIS et de chaque balise AtoN reçue sur le bus N2K. `group()` effondre
toutes ces séries en une seule table, `sort()` les ordonne par temps, et
`last()` renvoie **le point le plus récent, quel qu'en soit l'émetteur**.

Ce que `racing.js` appelle « la position du bateau » est donc la position du
dernier émetteur ayant écrit dans la fenêtre : nous, un cargo, ou une bouée.

C'est aussi l'explication du mystère de cardinalité noté le 15 septembre
(18 456 séries pour `navigation.position`) : une série par émetteur AIS.

## Mesure

**1 réponse(s) sur 1** proviennent d'une cible AIS ou d'une balise, et non du
bateau — en rejouant la requête de `racing.js` au caractère près, en gardant
seulement la colonne `context` qu'il jette.

| Mesure | Valeur |
|--------|--------|
| énumération des contextes | OK |
| contexte retenu pour le bateau | `vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f` |
| réponses polluées par l'AIS | 1 / 1 |
| skew après filtrage du contexte | EXPLOITABLE |
| instants acceptés, fenêtre 60 s | 12 |
| instants acceptés, fenêtre 300 s | 11 |

## Conséquence sur le jalon du 15 septembre

Le premier instantané historique « réussi sur données de production réelles »
(`status: COMPLETE`, `bounded_skew_ms: 1`) a été obtenu avec cette même requête
non filtrée. Un skew de 1 ms entre quatre faits écrits par des émetteurs
différents s'explique naturellement par la densité du trafic AIS. **Ce jalon ne
prouve donc pas ce qu'il annonçait** : il doit être rejoué avec un filtre de
contexte avant d'être considéré comme acquis.

## Étalonnage de l'instrument

Les trois états sont produits **à la demande** avant toute mesure, y compris le
délai dépassé, provoqué volontairement avec la forme `group()+sort()` et deux
secondes de délai.

```
bucket midnight_rider / jeton sha256[:16]=3e83dfafb0f92009
    mesure inexistante -> EMPTY                    EMPTY      0.05s  conforme
    last() pousse au moteur -> DATA                DATA       4.14s  conforme
    group()+sort() avec 2 s de delai -> TIMEOUT    TIMEOUT    2.00s  conforme
    ETALONNAGE=3/3
```

## Qui écrit dans navigation.position

```
schema.tagValues(context) : DATA en 0.1s, 3991 valeur(s)
    3991 contexte(s) au total : 3990 AIS/AtoN, 1 non-AIS

    Contextes NON-AIS (candidats pour le bateau lui-meme) :
    contexte                                           points  premier                  dernier
    --------------------------------------------------------------------------------------------------------
    vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401      21713  2026-07-23T21:48:<masque>  2026-07-23T22:25:<masque>

    CONTEXTE_BATEAU=vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f
    CONTEXTE_POINTS=21713
CONTEXTES=OK
```

## Le gagnant du last(), requête de racing.js rejouée

```
fait                 as_of                  contexte gagnant                               AIS ?
    --------------------------------------------------------------------------------------------------------
    latitude             2026-09-07T14:36:00Z   (ERREUR)                                       
    speed_over_ground    2026-09-07T14:36:00Z   vessels.urn:mrn:imo:mmsi:368217460             OUI <- ce n est pas notre bateau
    course_over_ground   2026-09-07T14:36:00Z   (ERREUR)                                       
    latitude             2026-09-07T14:26:00Z   (ERREUR)                                       
    speed_over_ground    2026-09-07T14:26:00Z   (ERREUR)                                       
    course_over_ground   2026-09-07T14:26:00Z   (ERREUR)                                       
    latitude             2026-09-07T14:16:00Z   (ERREUR)                                       
    speed_over_ground    2026-09-07T14:16:00Z   (ERREUR)                                       
    course_over_ground   2026-09-07T14:16:00Z   (ERREUR)                                       
    latitude             2026-09-07T14:06:00Z   (ERREUR)                                       
    speed_over_ground    2026-09-07T14:06:00Z   (ERREUR)                                       
    course_over_ground   2026-09-07T14:06:00Z   (ERREUR)                                       

    1 reponse(s) sur 1 proviennent d une cible AIS ou d une balise.
POLLUES=1
TOTAL_SONDES=1
```

## Skew, contexte filtré

```
contexte filtre : vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f

    fenetre 60 s
    as_of                  faits       skew ms  verdict
    ------------------------------------------------------------
    2026-09-07T14:36:00Z   4/4              97  ACCEPTE
    2026-09-07T14:31:00Z   4/4               1  ACCEPTE
    2026-09-07T14:26:00Z   4/4             196  ACCEPTE
    2026-09-07T14:21:00Z   4/4              49  ACCEPTE
    2026-09-07T14:16:00Z   4/4              79  ACCEPTE
    2026-09-07T14:11:00Z   4/4             149  ACCEPTE
    2026-09-07T14:06:00Z   4/4              48  ACCEPTE
    2026-09-07T14:01:00Z   4/4              96  ACCEPTE
    2026-09-07T13:56:00Z   4/4             149  ACCEPTE
    2026-09-07T13:51:00Z   4/4               1  ACCEPTE
    2026-09-07T13:46:00Z   4/4             148  ACCEPTE
    2026-09-07T13:41:00Z   4/4               3  ACCEPTE
    skew : min 1  median 88  max 196 ms
    fenetre 60 s : 12 complets, 12 acceptes, 0 indetermines

    fenetre 300 s
    as_of                  faits       skew ms  verdict
    ------------------------------------------------------------
    2026-09-07T14:36:00Z   4/4              97  ACCEPTE
    2026-09-07T14:31:00Z   4/4               1  ACCEPTE
    2026-09-07T14:26:00Z   4/4             196  ACCEPTE
    2026-09-07T14:21:00Z   4/4              49  ACCEPTE
    2026-09-07T14:16:00Z   4/4              79  ACCEPTE
    2026-09-07T14:11:00Z   4/4             149  ACCEPTE
    2026-09-07T14:06:00Z   4/4              48  ACCEPTE
    2026-09-07T14:01:00Z   4/4              96  ACCEPTE
    2026-09-07T13:56:00Z   4/4             149  ACCEPTE
    2026-09-07T13:51:00Z   4/4               1  ACCEPTE
    2026-09-07T13:46:00Z   4/4          200441  REJETE
    2026-09-07T13:41:00Z   4/4               3  ACCEPTE
    skew : min 1  median 88  max 200441 ms
    fenetre 300 s : 12 complets, 11 acceptes, 0 indetermines
FEN60_COMPLETS=12
FEN60_ACCEPTES=12
FEN60_SKEW_MIN=1
FEN300_COMPLETS=12
FEN300_ACCEPTES=11
FEN300_SKEW_MIN=1
SKEW_RESULTAT=EXPLOITABLE
```

## Note de confidentialité

Dépôt public : les valeurs à trois décimales ou plus sont masquées. Les
identifiants MMSI des cibles AIS apparaissant dans les contextes sont des
émissions publiques et non des données privées, mais seule une liste tronquée
est reproduite.
