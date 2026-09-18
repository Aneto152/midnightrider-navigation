# Defaut 63 - le cap etait publie en radians sous une cle qui dit degres

Chantier H8d, 2026-09-18. Statut : **SUCCESS**.

## 1. Ce que le defaut faisait

| etape | fichier | ce qui se passait |
|---|---|---|
| 1 | `mcp/servers/racing.js` | validait `0 <= cog <= 360`, donc toute valeur en radians (0 a 6,28) passait sans rien signaler |
| 2 | `mcp/servers/racing.js` | publiait la valeur brute de Signal K sous la cle `course_over_ground_degrees` |
| 3 | `mediaman/mcp_collector.py` | revalidait 0 a 360 : passait encore |
| 4 | `mediaman/mcp_collector.py` | etiquetait `unit="degrees_true"` : l unite annoncee etait fausse |
| 5 | `mediaman/content_provider.py` | ecrivait `Cap: {valeur}deg` dans l article |

Un bateau au cap 198 degres etait donc annonce a 3,45 degres. Trois
validations successives laissaient passer l erreur pour une seule raison :
tout intervalle plausible en degres contient l intervalle des radians. Aucun
test ne pouvait l attraper par hasard, il fallait savoir qu on le cherchait.

Aucun message reel n est jamais parti : toute la chaine MediaMan tourne en
DRY_RUN. Le contrat etait casse, pas encore consomme.

## 2. La preuve par le domaine, et non par la documentation

La convention SI de Signal K est un argument d autorite. Le domaine des
valeurs, lui, est une mesure : un cap exprime en degres depasse forcement 6,28
des que le bateau tourne un peu. Mesure sur nos propres lignes, filtre `self`
du defaut 58 en place.

| mesure | valeur |
|---|---|
| jours sondes | 365 |
| minimum | 0.000000 rad |
| maximum | 6.281400 rad, soit 359.8977 degres |
| lignes au total | 4078141 |
| lignes au-dela de 2*PI | **0** |
| lignes au-dela de 0,1 rad | 3626071 |
| exemple le plus recent au-dela de 0,1 rad | `2026-09-07T14:36:23.698Z` |
| sa valeur brute, et ce que l article disait | 1.752300 rad, annonce `1.7523 deg` |
| ce que l article dit maintenant | `100.3994 deg` |

Zero ligne au-dela de 2*PI sur 4078141 : le champ est en radians, sans
ambiguite. La barriere du script etait prete a tout annuler si le maximum
avait depasse 2*PI, car convertir un champ deja en degres aurait ete une faute
symetrique.

## 3. Le correctif

- conversion dans `cogRadiansToDegrees()`, appelee **une seule fois**, a la
  frontiere du serveur. La convertir en aval aurait laisse la valeur brute
  voyager sous une cle qui annonce des degres, c est-a-dire le defaut lui-
  meme.
- le domaine validee a l entree devient [0, 2*PI] et non plus [0, 360]. Une
  valeur au-dela fait echouer la collecte, bruyamment : si Signal K se mettait
  un jour a servir des degres, le serveur refuserait au lieu de publier un cap
  absurde.
- chaque instantane porte un bloc `units`, frere de `facts` et jamais un
  cinquieme fait, l ensemble des quatre etant valide exactement.
- `mediaman/mcp_collector.py` refuse un bloc `units` qui contredit le contrat.
  Un bloc absent est accepte, pour ne pas casser une chaine deja deployee.
- `mediaman/content_provider.py` n est PAS modifie : il ecrit deja
  `{valeur}deg`, et cette valeur est maintenant juste.

## 4. Ce que les tests verrouillent

| suite | resultat |
|---|---|
| `tests/mcp/test_defaut_63_cog_degres.py` (nouveau) | 8 passed |
| `tests/mcp/test_defaut_58_context_filter.py` | 6 passed |
| `tests/mcp/` | 55 passed |
| `tests/mediaman/` | 511 passed |

Les huit tests du defaut 63 interrogent le vrai `racing.js` par le protocole
MCP, avec un faux InfluxDB qui LIT la requete Flux. Quatre d entre eux
echouent sur le code d avant le correctif - conversion, borne 2*PI, echec au-
dela du domaine, bloc units - ce qui en fait des preuves et non des
decorations.

Deux suites existantes ont du etre rectifiees, et il faut le dire : la preuve
en negatif du defaut 58 interdisait la valeur brute du cap AIS, qui n apparait
plus telle quelle apres conversion ; elle interdit maintenant aussi sa forme
convertie. Et la suite de contrat injectait `45.5` comme reponse unique aux
quatre requetes, ce qui est un cap impossible en radians : la valeur devient
`3.5`, valide dans les quatre domaines a la fois.

## 5. Ce qui reste ouvert

- aucune copie de `racing.js` hors du depot :
  `~/.openclaw/workspace/mcp/racing.js` n existe pas, le depot est la seule
  source malgre ce que suggere `mcp/claude_desktop_config.example.json`.
- defaut 65, releve ici : `mediaman/mcp_collector.py` appelle
  `racing.get_position`, `racing.get_sog` et `racing.get_cog`, trois outils
  que `racing.js` ne declare pas - il n expose que `get_historical_snapshot`.
  Le chemin temps reel du collecteur est donc mort, et seuls des mocks le
  couvrent. A arbitrer : implementer les trois outils, ou retirer le chemin.
- la suite de contrat repond la meme charge aux quatre requetes. C est cette
  complaisance qui a laisse vivre le defaut 58 pendant trois jours ; elle n
  est pas corrigee ici, le fichier fait 911 lignes et ce serait un autre
  chantier.

## 6. Ce que ce chantier ne prouve pas

Le jeu de donnees est fige depuis le 2026-09-07 et notre cap valait 0 sur la
fenetre du jalon : rejouer ce jalon ne montrerait aucune difference, 0 radian
valant 0 degre. La demonstration repose donc sur le domaine mesure et sur les
huit tests, pas sur un rejeu. Une vraie verification demandera des donnees
fraiches, c est-a-dire le bateau en marche.
