# Etalonnage de tools/fluxprobe.py - 2026-09-17

Lecture seule cote InfluxDB. Aucun code de production, aucun service,
aucune unite, aucun conteneur n a ete modifie.

## Pourquoi cette etape existe

Quatre conclusions fausses ont ete commitees en deux jours (defauts 55,
56, 59, 60). Aucune ne vient d une erreur de raisonnement sur le bateau :
toutes viennent d une sonde de mesure improvisee pour l occasion. Cette
etape ne fait avancer aucune fonctionnalite de MediaMan. Elle rend
verifiables les etapes suivantes.

## La sonde

`tools/fluxprobe.py` impose trois disciplines, chacune verrouillee par des
tests de non-regression nommes d apres le defaut qu ils empechent :

| Discipline | Defaut evite | Mecanisme |
|------------|--------------|-----------|
| Quatre etats explicites DATA / EMPTY / TIMEOUT / ERROR, message obligatoire sur echec | 55, 59 | `FluxResult.__post_init__` refuse un echec muet |
| Interdiction de lire `rows[0]` | 60 | `single_row()` leve, `latest_row()` trie, `require_single_series()` exige |
| Denominateur = nombre de tentatives | 59 | `Tally.rate()` leve tant qu une tentative a echoue |

Tests : 45 tests, etat VERT.

## Etalonnage sur le vrai InfluxDB

Les quatre etats sont produits a la demande avant toute mesure, y compris
l erreur, provoquee volontairement avec du Flux invalide.

```
    bucket midnight_rider / jeton sha256[:16]=3e83dfafb0f92009
    mesure inexistante -> EMPTY                    EMPTY     0.06s  conforme 
    last() pousse au moteur -> DATA                DATA      4.58s  conforme 
    group()+sort() avec 2 s de delai -> TIMEOUT    TIMEOUT   2.00s  conforme delai depasse apres 2.0 s
    Flux volontairement invalide -> ERROR          ERROR     0.00s  conforme HTTP 400 : {"code":"invalid","message":"error @1:1-1:6: undefined iden
    etalonnage h7a : 4 tentative(s) = 1 DATA, 1 EMPTY, 1 TIMEOUT, 1 ERROR
ETALONNAGE=4/4
```

Resultat : 4/4

## Preuve empirique du defaut 60

```
    contexte du bateau : vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f
    instant reexamine  : 2026-09-07T13:46:00Z (celui qui se contredisait en H6c)

    champ                              fen.    series  rows[0]._time              latest_row()._time         identiques ?
    --------------------------------------------------------------------------------------------------------------------------
    navigation.position/lat            60           2  2026-09-07T13:45:59.922Z   2026-09-07T13:45:59.989Z   NON <- rows[0] ment
    navigation.position/lon            60           2  2026-09-07T13:45:59.922Z   2026-09-07T13:45:59.989Z   NON <- rows[0] ment
    navigation.speedOverGround/value   60           2  2026-09-07T13:45:59.774Z   2026-09-07T13:45:59.99Z    NON <- rows[0] ment
    navigation.courseOverGroundTrue/value 60           2  2026-09-07T13:45:59.775Z   2026-09-07T13:45:59.99Z    NON <- rows[0] ment
    navigation.position/lat            300          4  2026-09-07T13:42:39.334Z   2026-09-07T13:45:59.989Z   NON <- rows[0] ment
    navigation.position/lon            300          4  2026-09-07T13:42:39.334Z   2026-09-07T13:45:59.989Z   NON <- rows[0] ment
    navigation.speedOverGround/value   300          2  2026-09-07T13:45:59.774Z   2026-09-07T13:45:59.99Z    NON <- rows[0] ment
    navigation.courseOverGroundTrue/value 300          2  2026-09-07T13:45:59.775Z   2026-09-07T13:45:59.99Z    NON <- rows[0] ment

    defaut 60 : 8 tentative(s) = 8 DATA, 0 EMPTY, 0 TIMEOUT, 0 ERROR
MULTI_SERIES=8
DIVERGENCES=8
VERDICT_60=CONFIRME (8/8 reponses ou rows[0] n est pas le plus recent)
```

Verdict : CONFIRME (8/8 reponses ou rows[0] n est pas le plus recent)

## Combien de series derriere le contexte du bateau

Question ouverte pour le correctif de `racing.js` : si le contexte seul ne
designe pas une serie unique, filtrer le contexte ne suffira pas.

```
    navigation.position                  2 valeur(s) de tag source : N2K.1, N2K.2
    navigation.speedOverGround           2 valeur(s) de tag source : N2K.1, N2K.2
    navigation.courseOverGroundTrue      2 valeur(s) de tag source : N2K.1, N2K.2
    series par contexte : 3 tentative(s) = 3 DATA, 0 EMPTY, 0 TIMEOUT, 0 ERROR
```

## Quel tag distingue les series

```

    navigation.position / lat : 4 serie(s)
      table 0   _time=2026-09-07T13:42:39.334Z   _field=lat  _measurement=navigation.position  context=vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f  s2_cell_id=9926647161770999808  self=true  source=N2K.1
      table 1   _time=2026-09-07T13:42:37.821Z   _field=lat  _measurement=navigation.position  context=vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f  s2_cell_id=9926647161770999808  self=true  source=N2K.2
      table 2   _time=2026-09-07T13:45:59.922Z   _field=lat  _measurement=navigation.position  context=vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f  s2_cell_id=9926653758840766464  self=true  source=N2K.1
      table 3   _time=2026-09-07T13:45:59.989Z   _field=lat  _measurement=navigation.position  context=vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f  s2_cell_id=9926653758840766464  self=true  source=N2K.2

    navigation.speedOverGround / value : 2 serie(s)
      table 0   _time=2026-09-07T13:45:59.774Z   _field=value  _measurement=navigation.speedOverGround  context=vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f  self=true  source=N2K.1
      table 1   _time=2026-09-07T13:45:59.99Z    _field=value  _measurement=navigation.speedOverGround  context=vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f  self=true  source=N2K.2

    tags par serie : 2 tentative(s) = 2 DATA, 0 EMPTY, 0 TIMEOUT, 0 ERROR
```

## Ce que cette etape ne fait pas

- elle ne corrige pas `mcp/servers/racing.js` (defaut 58 toujours ouvert) ;
- elle ne rejoue pas le jalon du 15 septembre ;
- elle ne touche ni aux defauts 52, 53, 54, ni au defaut 44.
