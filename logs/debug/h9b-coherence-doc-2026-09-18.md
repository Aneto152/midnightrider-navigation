# H9b - la documentation canonique doit pointer vers ce qui existe

**Chantier** : h9b-v1
**Parent** : f59411b5a12c6bb3cfe5d9f979060d95a2b69d5c
**Commit de contenu** : 42b63390402c73e0b63f84921584da934681f412
**Statut des tests** : SUCCESS

## Ce qui a ete corrige

La section 4.7 de `docs/ARCHITECTURE-MASTER.md` declarait trois outils MCP
sous l en-tete **Source-Verified Tools**, chacun marque **Verified**, avec
des limites de fraicheur de 30, 15 et 15 secondes :

| Outil annonce | Limite annoncee | Realite |
|---|---|---|
| `racing.get_position` | 30 s | jamais declare par le serveur |
| `racing.get_sog` | 15 s | jamais declare par le serveur |
| `racing.get_cog` | 15 s | jamais declare par le serveur |

Ces trois lignes ne sont pas devenues fausses avec le temps : elles l etaient
a l ecriture. Le mot *Verified* y figurait sans qu aucune verification ait eu
lieu. C est tres probablement la que le defaut 65 a puise sa longevite - un
lecteur qui trouve une coche verte dans le document canonique ne va pas lire
le serveur pour confirmer.

La table est **remplacee et non effacee**. Un bloc de correction date explique
ce qui s est passe. Effacer aurait produit un document propre et une lecon
perdue.

## Renvois morts corriges dans la meme passe

| Ligne | Ce qui etait ecrit | Ce qui est vrai |
|---|---|---|
| section 4.7 | `tests/mediaman/test_mcp_collector.py` | supprime par H9 |
| section 13 | `docs/ARCHITECTURE-REFERENCE-2026-05-20.md` marque **CE DOCUMENT** | le document est `docs/ARCHITECTURE-MASTER.md` |
| section 13 | `docs/ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md` | supprime en phase H |
| section 13 | `docs/HARDWARE/INSTRUMENT-INVENTORY.md` | fusionne puis supprime |
| section 13 | `docs/GRAFANA-UNIT-CONVERSIONS.md` | `docs/units/UNIT-CONVERSIONS-GRAFANA.md` |
| section 9 | mention fusionnee avec accents inverses | reformulee sans chemin |

La reference canonique du bord se designait elle-meme par le nom d un fichier
qui n existe plus. Un lecteur qui aurait suivi ce renvoi serait tombe sur rien.

## Deux commentaires de code

- `mediaman/mcp_collector.py` : l exemple du champ `wire_tool_name` citait
  `"get_position"`, un outil supprime.
- `mediaman/mcp_client.py` : un commentaire ecrit par H9 affirmait que le
  defaut 63 avait ete annonce *trois ans* avant d etre mesure. Ce chiffre
  n a jamais ete mesure. Il est remplace par *longtemps*.

## La barriere installee

`tests/mcp/test_h9b_coherence_doc_code.py` verifie quatre choses :

1. tout chemin cite entre accents inverses dans l architecture maitresse
   existe - sauf s il est ignore par git, ou hors du depot, ou porte dans
   une liste d exceptions nommees ou chaque entree doit expliquer sa raison ;
2. les outils declares par `mcp/servers/racing.js` et ceux autorises par la
   liste blanche de `mediaman/mcp_client.py` forment le meme ensemble ;
3. le serveur declare exactement deux portes ;
4. un nom d outil supprime ne peut apparaitre dans l architecture maitresse
   que dans le bloc de correction, jamais dans une table de ce qui existe.

Cette suite a ete executee sur le depot **avant** correction : trois de ses
six tests echouent. Elle mesure donc quelque chose. Une barriere qu on
n a jamais vue refuser ne prouve rien.

## Tests

| `h9b-garde` | ============================== 6 passed in 0.09s =============================== |
| `suite-mcp` | ============================= 74 passed in 39.44s ============================== |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 21.65s ======================= |

## Ce que H9b n a pas fait

- Le defaut 67 reste ouvert : `tests/mcp/js/test-all-mcp.js` teste sept
  serveurs par des noms de fichiers inexistants, `mcp/package.json` et
  `mcp/README.md` renvoient a un troisieme chemin encore different, et
  `docs/ops/RECOVERY-GUIDE-SAFE.md` a un quatrieme. Le harnais est mort et
  ses trois renvois le sont aussi.
- `validate_capabilities()` dans `mediaman/mcp_client.py` ne controle au
  demarrage que `get_historical_snapshot`. La porte que le direct emprunte,
  `get_snapshot`, n est pas validee. L asymetrie contredit la these de H9 et
  reste a corriger.
- Les 41 lignes de `logs/oc-actions.log` estampillees avec un `Z` final ne
  sont pas reecrites. Un journal append-only ne se recrit pas pour des
  raisons cosmetiques, et rien ne le parse. H9b ecrit au format du standard.

## Etat du depot au demarrage

Du travail non commite appartenant a d autres chantiers etait present. H9b ne
l a pas ecarte : il a verifie que la liste de ses cibles et celle des fichiers
modifies ailleurs etaient disjointes, a releve leur empreinte avant, l a
recontrolee apres, et n a jamais indexe globalement.
