# H9 - un seul chemin de collecte

Date : 2026-09-18T20:02:45Z
Version du script : h9-v1
Commit de contenu : 019c4ef6c13938885d54fb8bafd4e2484c2b6f73
Parent : e64f3ca5b51a83ed74772346c86fcbc02a003dc6

## 1. Ce que le defaut faisait

`mediaman/mcp_collector.py` exposait deux methodes de collecte.
`collect_historical()` interrogeait `racing.get_historical_snapshot`, seul
outil que `mcp/servers/racing.js` declare. `collect()` interrogeait
`racing.get_position`, `racing.get_sog` et `racing.get_cog`, trois outils que
ce serveur n a jamais declares : l aiguillage `handleTool` les faisait tomber
dans son `default`, qui leve `Unknown tool`.

Le chemin temps reel ne pouvait donc rien collecter. Il etait pourtant
atteignable depuis `etc/systemd/system/mediaman-events.service`, et le
defaut par defaut du code - et non de l unite - etait `mcp`. Quiconque
lancait `python3 -m mediaman.event_entrypoint` a la main prenait ce chemin.
Le commentaire de l unite invitait explicitement a y basculer.

## 2. Pourquoi il a survecu

`tests/mediaman/test_mcp_collector.py` comptait 627 lignes et 32 tests. Les
32 portaient sur ce chemin. En face, `collect_historical` - celui qui produit
reellement les articles - n avait que cinq sites d appel dans deux fichiers.

Le chemin qui n a jamais fonctionne avait six fois plus de tests que celui
qui marche. Trois d entre eux verifiaient consciencieusement que la liste
blanche de `mcp_client.py` contenait bien les trois outils inexistants.

Et la description que cette liste blanche donnait de `racing.get_cog` etait :
`Course over ground (degrees, radians)`. Les deux unites a la fois, ecrites
sans broncher. C etait le defaut 63 annonce noir sur blanc, des l origine,
et personne ne l a lu.

## 3. Ce qui a ete decide

Denis, le 2026-09-18 : maintenir les deux usages, le direct pour la course et
l historique comme banc d essai, avec l architecture la plus proche possible
entre les deux, sans ecart autre que necessaire.

L ecart mesure avant decision : huit differences, dont deux seulement
etaient necessaires.

| Aspect | Historique | Temps reel | Necessaire |
|---|---|---|---|
| Nombre d appels | 1 | 3 | non |
| Controle de derive | oui | impossible | non |
| Filtre `self` | oui | absent | non |
| Conversion du cap | oui | absente | non |
| Bloc `units` | oui | absent | non |
| Complétude | 4 champs exactement | partielle toleree | non |
| Limite de fraicheur | absente | 30/15/15 s | **oui** |
| Qui choisit la borne haute | l appelant | implicite | **oui** |

## 4. Le correctif

Un moteur, `collectSnapshot(startUtc, endUtc)`, et deux portes minces.
`get_historical_snapshot` survit inchangee, en adaptateur. `get_snapshot`
prend deux bornes explicites ; le direct, c est cette porte avec `end_utc`
place a l instant ou l on consulte.

Cote collecteur, `_collect_snapshot()` porte le corps commun ;
`collect_historical()` et `collect_current()` ne different que par le tuple
(outil, bornes, limite de fraicheur).

Deux points de conception meritent d etre notes.

**Le serveur ne demande jamais l heure.** La borne haute arrive toujours en
parametre. Rejouer le passe a travers le code du direct ne demande donc de
tromper aucune horloge : il suffit de passer une borne passee. La porte
derobee de test que j envisageais est devenue inutile, et c est la
formulation de Denis qui l a rendue inutile.

**Les deux bornes sont normalisees.** Sans cela les deux portes produisaient,
pour le meme intervalle, des requetes Flux textuellement differentes : la
porte historique calcule sa borne basse avec `toISOString()` et obtient
`.000Z`, la porte de plage recoit ce que l appelant a ecrit. Meme instant,
autre chaine. La normalisation est ce qui rend la convergence verifiable au
caractere pres, et non seulement semantiquement.

## 5. Ce qui a failli passer

`mediaman/mcp_client.py` porte une liste blanche d outils.
`racing.get_snapshot` n y figurait pas. Sans l ajout, `collect_current()`
aurait echoue en production sur `Tool not allowlisted` - et aucun des tests
ne l aurait vu, parce que leurs faux clients court-circuitent la liste
blanche. C est la meme forme que le defaut 65 : un contrat que les mocks
rendent invisible. Trouve en lisant le code, pas en executant les tests.

## 6. Ce que les tests verrouillent

| h9 - chemin unique (serveur) | `============================== 13 passed in 8.07s ==============================` |
| h9 - collect_current (collecteur) | `============================== 16 passed in 0.30s ==============================` |
| defaut 58 - filtre de contexte | `============================== 6 passed in 6.49s ===============================` |
| defaut 63 - cap en degres | `============================== 8 passed in 5.36s ===============================` |
| suite tests/mcp | `============================= 68 passed in 39.46s ==============================` |
| suite tests/mediaman | `======================= 495 passed, 2 warnings in 21.88s =======================` |

Les six suites sont vertes.

Les verrous structurels, qui sont le vrai apport de H9 :

- un seul constructeur de requete Flux dans `racing.js`, compte par un test ;
- les deux portes emettent des requetes identiques au caractere pres ;
- les deux portes rendent des faits et des unites identiques ;
- les defauts 58 et 63 sont reverifies par la porte neuve ;
- les trois noms d outils morts sont interdits de retour dans le collecteur.

## 7. Ce que ce chantier ne prouve pas

Rien n a ete ingere dans InfluxDB depuis le 2026-09-07T14:36:24Z. Une
collecte en direct sur le Pi ne trouverait donc aucune donnee dans les trente
dernieres secondes et rendrait, correctement, un resultat incomplet. La
preuve que `collect_current()` fonctionne sur de vraies donnees repose sur le
banc d essai : `reference_time` place la borne haute sur un instant
reellement enregistre, et le code execute est celui du direct, ligne pour
ligne. La verification de bout en bout attend que le bateau navigue.

Par ailleurs `event_detector.py` ne detecte aucun evenement nautique : ses
cinq types sont techniques. H9 rend le chemin du direct fonctionnel ; il ne
lui donne pas encore quelque chose d interessant a raconter. C est l objet
du chantier suivant.

## 8. Defaut ouvert en passant

`tests/mcp/js/test-all-mcp.js` declare tester sept serveurs MCP par des noms
de fichiers - `racing-server.js`, `astronomical-server.js` - dont aucun
n existe : les fichiers reels s appellent `racing.js`, `astronomical.js`. Il
fixe aussi `INFLUX_ORG = 'MidnightRider'` et `BUCKET = 'signalk'`, qui ne
sont pas la configuration reelle. Ce harnais est mort. Constate, non touche :
defaut 67, hors perimetre de H9.
