# Rejeu du jalon du 2026-09-15

**Date** : 2026-09-18 | **Chantier** : H8b | **Statut** : SUCCESS

Aucune coordonnee dans ce document : `docs/DECISIONS/MEDIAMAN-HISTORICAL-DRY-RUN.md` pose que les valeurs de faits ne sont
pas consignees dans ce depot, qui est public.

## 1. Pourquoi ce rejeu

Le jalon du 2026-09-15 declarait la chaine validee de bout en bout : `exit code 0`, quatre faits COMPLETE, `bounded_skew_ms 1`,
`source_timestamp 2026-09-07T14:36:24.298Z`. Ce run interrogeait InfluxDB **sans filtre de contexte** : le defaut 58.

## 2. Mesure sur la fenetre exacte du jalon

Fenetre : 2026-09-07T14:35:26.000Z -> 2026-09-07T14:36:26.000Z, soit 60 s finissant a `2026-09-07T14:36:26Z`.

| fait | venait d une cible AIS | la valeur change |
|---|---|---|
| `latitude` | **oui** | **oui** |
| `longitude` | **oui** | **oui** |
| `speed_over_ground` | **oui** | **oui** |
| `course_over_ground` | **oui** | **oui** |

- faits qui venaient d une cible AIS : **4 / 4**
- faits dont la valeur change avec le correctif : **4 / 4**
- distance entre la position publiee le 15 septembre et la vraie : **11.04 milles marins**

## 3. Prouve faux, et non seulement inverifiable

> **Rectification du 2026-09-18, chantier H8c.** La premiere version de ce
> paragraphe comptait les contextes ecrivant a NOTRE horodatage gagnant, apres
> filtrage. La question porte sur l instant que l **ancienne** requete
> retenait, celui qui a produit le jalon. La mesure ne repondait pas a la
> question posee : elle est refaite ci-dessous, au bon instant.

| fait | instant retenu par l ancienne requete | lignes a cet instant | contextes | dont AIS | notre ligne y est | = `source_timestamp` du jalon |
|---|---|---|---|---|---|---|
| `latitude` | `2026-09-07T14:36:24.298Z` | **1** | 1 | 1 | non | oui |
| `longitude` | `2026-09-07T14:36:24.298Z` | **1** | 1 | 1 | non | oui |
| `speed_over_ground` | `2026-09-07T14:36:24.297Z` | **1** | 1 | 1 | non | non |
| `course_over_ground` | `2026-09-07T14:36:24.297Z` | **1** | 1 | 1 | non | non |

- faits dont le contexte gagnant etait une cible AIS : **4 / 4**
- faits ou plusieurs lignes partagent l instant retenu : **0 / 4**, au maximum
  **1** ligne(s)
- faits ou notre propre ligne partageait cet instant : **0 / 4**

Une seule ligne existait a l instant retenu, pour chacun des 4 faits : l
ancienne requete etait **deterministe**. Rejouee le 2026-09-18 sur le meme jeu
de donnees, fige depuis le 2026-09-07, elle rend un contexte AIS pour **4
fait(s) sur 4**. La preuve du 2026-09-15 est donc **fausse**, et pas seulement
inverifiable. Pour **2 fait(s) sur 4**, l instant retenu est exactement le
`source_timestamp` consigne le 2026-09-15.

## 4. Provenance reelle de nos quatre faits

Mesuree avec `group()` puis `sort(columns: ["_time"])` puis `last(column: "_time")` - sans le `sort()`, `last()` rend la derniere
ligne de la derniere serie et non le point le plus recent, piege sur lequel je suis retombe trois fois.

| chemin | sources ayant ecrit NOTRE contexte |
|---|---|
| `navigation.courseOverGroundTrue` | `N2K.1`, `N2K.2` |
| `navigation.position` | `N2K.1`, `N2K.2` |
| `navigation.speedOverGround` | `N2K.1`, `N2K.2` |

`N2K.0` n apparait pas : c est le recepteur AIS, il n ecrit jamais notre contexte.

## 5. Rejeu

| | |
|---|---|
| parametres | identiques au 2026-09-15 : `as_of=2026-09-07T14:36:26Z`, fenetre 60 s |
| `DRY_RUN` | `true`, impose par le programme, verifie en phase 13 |
| Telegram | aucun identifiant accede, aucun envoi |
| resultat | **SUCCESS** |
| empreinte du contenu | `b36f4233caab5c1d...` |
| tests du defaut 58 | 6 passed |
| suite `tests/mcp/` | 47 passed |

Le `publication_id` est le SHA-256 de `race_id:as_of:window:contenu`. Il prouve qu un contenu a ete produit et
permet de le recomparer plus tard, sans rien reveler de sa valeur.

## 6. Caviardage

H8a avait ecrit la position du bateau dans `mcp/servers/racing.js` et dans `logs/debug/defaut-58-filtre-contexte-2026-09-17.md`. Retiree de la
version courante. Elle reste dans l historique git du commit `8919130` : l historique ne se reecrit pas, et le dire est la seule chose honnete.

## 7. Ce qui reste ouvert

- **defaut 63** : `course_over_ground_degrees` porte une valeur en radians, sans conversion. Contrat publie, arbitrage requis.
- **defaut 61** : `scripts/commit-logs.sh` commite l index entier.
- **defaut 62** : la Deployment Checklist de `etc/systemd/system/README.md` copie encore `*.service` en bloc.
- **SEC-2026-09-14-01** : l ancien jeton InfluxDB expose n est toujours pas revoque.
- InfluxDB n a plus rien recu depuis le 2026-09-07 : aucun rejeu ne peut rien prouver sur l exploitation en direct.

## 8. Rectifications du 2026-09-18 (H8c)

7 endroits ou une conclusion avait ete ecrite **avant** la mesure, puis jamais
relue apres elle.

| ce qui etait ecrit | ce qui est vrai |
|---|---|
| le paragraphe 3, premiere version : *un seul contexte avait ecrit a l horodatage gagnant* | le comptage portait sur notre horodatage **apres** filtrage, pas sur l instant retenu par l ancienne requete. Refait ci-dessus. |
| le titre du paragraphe 3 : *Inverifiable, et non prouve faux* | titre fige ecrit d avance, qui contredisait son propre corps. Il est maintenant engendre depuis la mesure. |
| le message du commit `1fa2853f91f1925c96a0972e57553f656fd1cb43` : *inverifiable, plusieurs contextes partageant l horodatage gagnant* | cette affirmation est fausse : au bon instant, 1 ligne(s) au maximum partagent l instant retenu. Un message de commit ne se reecrit pas : il est rectifie ici et dans `logs/oc-actions.log`. |
| `logs/oc-actions.log`, ligne du 2026-09-18T14:16:59 : *preuve du 15 conservee et marquee inverifiable* | rectifiee par ajout, la ligne d origine n est pas reecrite. |
| `logs/latest.json`, entree h8b, `files_modified` | omettait `tests/mcp/test_defaut_58_context_filter.py` et citait ce constat, qui appartient au commit de journal. Corrige, et le caviardage a porte sur **trois** fichiers et non deux. |
| `logs/latest.json`, `commit_chain` | les deux commits de journal `h8a_journal` et `h8b_journal` n y figuraient pas : la chaine sautait de `h8a_content` a `h8b_content`. Completee. |
| la decision : *our_sources_in_that_window: measured with group() then sort() then last()* | mesure par `schema.tagValues` sur le tag `source`, avec le predicat `r.self == "true"`. Corrige. |

Regle retenue : **aucune prose ecrite d avance** - message de commit, titre de
section, ligne de journal - ne doit affirmer une conclusion qui depend d une
mesure. Elle doit etre engendree depuis le resume de mesure, ou rester neutre.

Ce que H8b avait etabli et que cette mesure ne remet pas en cause : sur la
fenetre exacte du jalon, les quatre faits publies venaient d une cible AIS, a
11,04 milles marins de la position reelle du bateau.
