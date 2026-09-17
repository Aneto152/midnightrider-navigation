# Reconnaissance de la chaîne historique MediaMan — 2026-09-17

Lecture seule. Aucun service, aucune unité, aucun conteneur, aucun code de
production n'a été modifié par cette reconnaissance.

## Pourquoi cette étape existe

`mediaman/historical_entrypoint.py` implémente une chaîne complète en 14 phases :
validation d'environnement, `MCPClient` → `mcp/servers/racing.js` → InfluxDB,
`HistoricalMCPProvider`, `PublicationBridge`, `DryRunSender`. Elle est testée par
`tests/mediaman/test_historical_e2e_offline.py` — **qui remplace `MCPClient` et
`MCPCollector` par des doublures**. La chaîne réelle n'avait donc jamais été
exécutée une seule fois, et rien dans le dépôt ne l'appelle : aucun script,
aucune unité systemd.

`racing.js` impose une contrainte que personne n'avait mesurée : les quatre
faits obligatoires (latitude, longitude, SOG, COG) doivent être horodatés à
moins de **1000 ms** les uns des autres (`SKEW_LIMIT_MS`). Si les données
réelles ne satisfont pas cette contrainte, aucun instant de l'histoire ne
produira jamais d'article, et tout le reste du chantier serait bâti sur du
sable. C'est la première chose mesurée ici.

## Verdict

**FAITS_MANQUANTS** — Au moins un des 4 faits obligatoires n'a aucune donnée dans le bucket.

| Mesure | Valeur |
|--------|--------|
| instants testés | 0 |
| instants réunissant les 4 faits | 0 |
| instants sous la limite de 1000 ms | 0 |
| `as_of` retenu | `2026-09-17T01:59:24Z` |
| réponse de `racing.js` | ERREUR |
| skew mesuré par `racing.js` | n/d ms |
| code de sortie de `historical_entrypoint` | 1 |

## Reconnaissance InfluxDB

```
    URL    : http://localhost:8086
    org    : MidnightRider
    bucket : midnight_rider
    jeton  : present, empreinte sha256[:16] = 3e83dfafb0f92009
    sante  : pass
    buckets: midnight_rider

    Les 4 faits OBLIGATOIRES de racing.js (measurement / field) :
    fait                 measurement                        field  premier point          dernier point          points/30j
    ----------------------------------------------------------------------------------------------------------------------
    latitude             navigation.position                lat     ERREUR TimeoutError
    longitude            navigation.position                lon     ERREUR TimeoutError
    speed_over_ground    navigation.speedOverGround         value   ERREUR TimeoutError
    course_over_ground   navigation.courseOverGroundTrue    value   ERREUR TimeoutError

    VERDICT : latitude, longitude, speed_over_ground, course_over_ground n a aucune donnee. racing.js leve
    'Collection incomplete' et AUCUN instant ne produira jamais d article.
RESULTAT=FAITS_MANQUANTS

```

## Appel direct de racing.js en JSON-RPC

```
    initialize  : {"name": "racing-mcp-server", "version": "2.0"}
    tools/list  : get_historical_snapshot
    tools/call  : ERREUR {"code": -32603, "message": "Collection incomplete: latitude missing or incomplete"}
MCP_VERDICT=ERREUR
    stderr du serveur (tronque) :
      {"timestamp":"2026-09-17T02:59:<masque>Z","eventType":"STARTUP","version":"2024-11-05","bucket":"midnight_rider"}
      {"timestamp":"2026-09-17T02:59:<masque>Z","eventType":"STARTUP","method":"initialize","version":"2024-11-05"}
      {"timestamp":"2026-09-17T02:59:<masque>Z","eventType":"DATA_OUT","method":"tools/list","count":1}
      {"timestamp":"2026-09-17T02:59:<masque>Z","eventType":"DATA_IN","asOfUtc":"2026-09-17T01:59:24Z","windowSeconds":300,"startTime":"2026-09-17T01:54:<masque>Z"}
      {"timestamp":"2026-09-17T02:59:<masque>Z","eventType":"DATA_OUT","statusCode":200,"bytes":2}
      {"timestamp":"2026-09-17T02:59:<masque>Z

```

## Exécution de historical_entrypoint

```

```

## Note de confidentialité

Ce dépôt est public. Aucune coordonnée du bateau n'est reproduite dans ce
rapport : les valeurs à trois décimales ou plus sont remplacées par
`<masque>`, et la présence d'un fait est rapportée sans sa valeur.
