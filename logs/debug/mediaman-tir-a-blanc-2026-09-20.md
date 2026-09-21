# Mediaman - tir a blanc de la chaine historique

**Chantier** : mediaman-tir-v2
**Base** : 2fab770b781a8899c7fb97d00b730e833e271c3c
**Horodatage** : 20260921T224535Z

Rejeu de ce que le 2026-09-18 a fait une fois : produire un article a
partir d un instantane reel d InfluxDB, sans rien envoyer. `DRY_RUN=true`,
SQLite temporaire, aucun identifiant Telegram dans l environnement du
sous-processus, aucune ecriture InfluxDB - `mcp/servers/racing.js` ne
contient aucun appel a l API d ecriture, verifie avant de tirer.

## Ce qui a ete verifie avant, dans le code, des deux cotes du fil

| Point du contrat | `mcp_collector.py` exige | `racing.js` emet |
|---|---|---|
| cles de faits | les 4 | les 4 |
| unites | `degrees`, `degrees`, `m_per_s`, `degrees_true` | idem |
| enveloppe | `content[0].type == "text"` | idem |
| schema | `as_of_utc` + `window_seconds`, sans extra | idem |

## Les deux tirs

| Tir | Fenetre | Resultat |
|---|---|---|
| 1 - rejeu | `2026-09-07T14:36:26Z` + 60s | **reussi** |
| 2 - recent | `2026-09-21T22:43:36Z` + 60s | **echoue (code 1)** |

Source du jeton : `/home/aneto/midnightrider-navigation/.env` - contenu jamais affiche, jamais ecrit,
jamais transporte.
Taille du dernier article produit : 362 octets. Le contenu reste
dans `/tmp/mediaman-tir1-20260921T224535Z.txt` sur la machine : il porte la position du bateau et n a
rien a faire dans un depot public.

## Journal de l entree, fin de course

```
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN historical request contract valid
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN MCP client started
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN temporary SQLite state store initialized
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN MCPCollector initialized
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN historical provider created via factory
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN DryRunSender initialized with canonical parameter support
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN PublicationBridge initialized
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_OUT content generated: 362 bytes
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_OUT content validated
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN publication created: id=289dd71fce384c2ca6f2b2e6278b2f7c798aa89ebea2a6e9af4866971f6745e6
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_OUT publication published: state=SENT, provider_id=dry-run:d894656fce4dc85c
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_OUT dry-run publication successful and verified
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_OUT MCP client terminated
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] SHUTDOWN historical entrypoint completed successfully
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] STARTUP historical entrypoint
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN environment variables validated
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN historical request contract valid
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN MCP client started
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN temporary SQLite state store initialized
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN MCPCollector initialized
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN historical provider created via factory
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN DryRunSender initialized with canonical parameter support
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_IN PublicationBridge initialized
[2026-09-21T18:45:37] [ERROR] [mediaman-historical-entrypoint] ERROR: Content generation failed: Historical collection failed: ['racing.get_historical_snapshot: MCPServerError: Server error -32603: Collection incomplete: latitude missing or incomplete']
[2026-09-21T18:45:37] [INFO] [mediaman-historical-entrypoint] DATA_OUT MCP client terminated
```

## Journal du collecteur, fin de course

```
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector STARTUP: mode=current, tool=racing.get_snapshot, args={'end_utc': '2026-09-07T14:36:26Z', 'start_utc': '2026-09-07T14:35:56Z'}
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector DATA_IN: calling racing.get_snapshot
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector DATA_OUT: status=complete, facts=4, succeeded=1, failed=0
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector SHUTDOWN
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector STARTUP: mode=current, tool=racing.get_snapshot, args={'end_utc': '2026-09-07T14:36:26Z', 'start_utc': '2026-09-07T14:35:56Z'}
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector DATA_IN: calling racing.get_snapshot
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector DATA_OUT: status=complete, facts=4, succeeded=1, failed=0
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector SHUTDOWN
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector STARTUP: mode=current, tool=racing.get_snapshot, args={'end_utc': '2026-09-07T14:36:26Z', 'start_utc': '2026-09-07T14:35:56Z'}
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector DATA_IN: calling racing.get_snapshot
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector DATA_OUT: status=partial, facts=4, succeeded=1, failed=0
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector SHUTDOWN
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector STARTUP: mode=current, tool=racing.get_snapshot, args={'end_utc': '2026-09-07T14:36:26Z', 'start_utc': '2026-09-07T14:35:56Z'}
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector DATA_IN: calling racing.get_snapshot
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector DATA_OUT: status=partial, facts=4, succeeded=1, failed=0
[2026-09-20T18:27:25] [INFO] [mediaman-mcp-collector] Collector SHUTDOWN
[2026-09-21T18:45:37] [INFO] [mediaman-mcp-collector] Collector STARTUP: mode=historical, tool=racing.get_historical_snapshot, args={'as_of_utc': '2026-09-07T14:36:26Z', 'window_seconds': 60}
[2026-09-21T18:45:37] [INFO] [mediaman-mcp-collector] Collector DATA_IN: calling racing.get_historical_snapshot
[2026-09-21T18:45:37] [INFO] [mediaman-mcp-collector] Collector DATA_OUT: status=complete, facts=4, succeeded=1, failed=0
[2026-09-21T18:45:37] [INFO] [mediaman-mcp-collector] Collector SHUTDOWN
[2026-09-21T18:45:37] [INFO] [mediaman-mcp-collector] Collector STARTUP: mode=historical, tool=racing.get_historical_snapshot, args={'as_of_utc': '2026-09-21T22:43:36Z', 'window_seconds': 60}
[2026-09-21T18:45:37] [INFO] [mediaman-mcp-collector] Collector DATA_IN: calling racing.get_historical_snapshot
[2026-09-21T18:45:37] [ERROR] [mediaman-mcp-collector] Collector ERROR: racing.get_historical_snapshot: MCPServerError: Server error -32603: Collection incomplete: latitude missing or incomplete
[2026-09-21T18:45:37] [INFO] [mediaman-mcp-collector] Collector DATA_OUT: status=failed, facts=0, succeeded=0, failed=1
[2026-09-21T18:45:37] [INFO] [mediaman-mcp-collector] Collector SHUTDOWN
```

## Ce que ces deux tirs mesurent

Le point 5 du document de decision affirme qu InfluxDB ne contient plus
rien apres `2026-09-07T14:36:24Z`. Le tir 2 porte sur une fenetre vieille
de deux minutes : son resultat est la mesure de cette affirmation, pas un
espoir decu.

## Ce que ce chantier n a pas fait

Aucune ecriture InfluxDB. Aucun envoi Telegram. Aucun geste systemd,
aucun geste docker. Aucune base persistante. Aucun contenu d article dans
le depot.
