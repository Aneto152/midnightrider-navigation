# Le perimetre de la mesure porte son nom

**Chantier** : h14a-bis-v1
**Base** : f761aedaf986e6a6645202f284c9ca971f1be570
**Commit de contenu** : 0bc2a69e0ba37f79e8d57c7d728ffd54663cb995

## Ce que H14a avait ferme, et comment

Le 2026-09-20 au matin, H14a a ferme le defaut 89 : le guide de secours
prescrivait `systemctl enable --now midnight-logsync.timer`, unite
desarmee par H7e trois jours plus tot. La mesure posee pour que cela ne
recommence pas tenait en une ligne :

```python
for chemin in _documents_markdown(["docs"]):
```

Elle a rendu vert. Elle rendait vert a raison : `docs/` etait propre.

## Ce qu elle ne regardait pas

Trois lignes, dans deux endroits que personne n avait mesures :

| Fichier | Ligne | Contenu |
|---|---|---|
| `etc/systemd/system/README.md` | 153 | `sudo systemctl enable --now midnight-logsync.timer`, dans un bloc pret a coller |
| `etc/systemd/system/midnight-logsync.service` | 5 | `# Retablir par :  sudo systemctl enable --now midnight-logsync.timer` |
| `etc/systemd/system/midnight-logsync.timer` | 5 | la meme ligne |

Dans le README, cette commande figure **huit lignes au-dessus** de **Ne
pas la reparer**. Dans les unites, **trois lignes sous** `NE PAS
REINSTALLER`. Le document se contredit lui-meme, et c est la version
executable qui gagne, parce que c est elle qu on colle.

Deux lignes de plus, dans ces memes unites, proposaient encore la copie
en masse que H14a venait pourtant de retirer du README :

```
#   sudo cp etc/systemd/system/*.service /etc/systemd/system/
```

## Dixieme fois cette semaine

C est le meme defaut que je repete depuis six jours, sous des formes
differentes : **une mesure plus etroite que son nom**.

| # | Ou | La mesure disait | Elle mesurait |
|---|---|---|---|
| 1 | H11 | tous les jetons InfluxDB | pas `INFLUX_DB_` |
| 2 | H12 | tous les chemins cites | seulement les accents inverses |
| 3 | H12 | defaut 67 ferme | le guide en parlait, rien de plus |
| 4 | H12 | `expect 80 passed` | la suite en comptait 85 |
| 5 | 20/09 | les points de position | filtrait sur `value`, absent de `lat`/`lon` |
| 6 | H12c | les defauts orphelins | `\d+\b` ne voyait pas `20b` |
| 7 | H13 | le bucket `signalk` | attrapait aussi `signalk-cloud` |
| 8 | H13 | les chemins en preuve | coupait `latest.json` en `latest.js` |
| 9 | H14a | le detecteur de prescriptions | aveugle a la continuation `\` |
| 10 | **ici** | aucun document n arme l unite | **seulement `docs/`** |

Les cinq premieres pechaient par defaut, les suivantes par exces, celle-ci
par perimetre. Aucune n a ete trouvee en relisant. Toutes en executant.

## Ce que ce chantier fait

- les cinq lignes sont retirees : le README ne propose plus de
  retablissement, les deux en-tetes d unite non plus, et les deux
  mentions de copie en masse deviennent un avertissement
- le perimetre du controle passe de `docs/*.md` aux fichiers de procedure
  de `docs/`, `etc/`, `scripts/` et de la racine : `.md`, `.sh`,
  `.service`, `.timer`, `.py`. **88 fichiers** au lieu des
  seuls markdown de `docs/`
- `logs/` et `tests/` restent dehors, nommement, avec la raison ecrite
  dans le code : les constats et les echantillons citent la ligne
  interdite a dessein
- trois controles nouveaux portent sur le **perimetre** : il doit couvrir
  les quatre fichiers ou la prescription a reellement vecu, il doit
  ecarter les deux racines nommees, et un echantillon bati sur les deux
  formes reelles du jour doit rendre rouge

## Ce que ce chantier ne fait pas

Les unites installees sur la machine ne sont pas redeployees. Elles
divergent deja du depot (defaut 91), et seules des lignes de commentaire
changent ici : un controle le verifie sur le diff, `0` ligne non
commentaire modifiee.

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 39 passed in 0.60s ============================== |
| `suite-mcp` | ============================= 107 passed in 39.87s ============================= |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 22.41s ======================= |

## Portee

Aucun service, aucun conteneur, aucune unite installee, aucune ecriture
InfluxDB. **Ce chantier ne modifie que des fichiers du depot.**

---
*Ecrit par H14a-bis le 2026-09-20T20:18:52.*
