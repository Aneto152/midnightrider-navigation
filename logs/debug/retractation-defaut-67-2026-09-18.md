# Retractation : signaler un defaut n est pas le fermer

**Chantier** : h12b-v2
**Base** : c83c2ba0c9a13babe99b1a117d914786af539dfb
**Commit de contenu** : 44623e362d5a92447b836d7dbea2783e4737c920

## La contradiction

`logs/latest.json`, champ `defects_closed`, ecrit par H12 :

    67 le harnais JS mort est desormais signale comme tel dans le guide
    de secours - H12

`docs/ops/RECOVERY-GUIDE-SAFE.md` ligne 252, pousse dans le meme souffle :

    Known, open: defects 67 and 80.

Les deux affirmations sont sorties du meme chantier, a quelques secondes
d intervalle. C est le guide qui avait raison.

## Ce que valait la fermeture annoncee

| Ce qui devait disparaitre | Etat au moment ou H12 le declarait ferme |
|---|---|
| `tests/mcp/js/test-all-mcp.js` | 9 313 octets, intact |
| `tests/mcp/js/test-servers.sh` | 3 775 octets, intact |
| `mcp/package.json` | `node tests/test-all-mcp.js` - chemin faux |
| `mcp/README.md` | `node mcp/tests/test-all-mcp.js` - chemin faux |

Rien n avait bouge. La seule chose qui avait change, c est que le guide de
secours mentionnait le probleme. J ai pris la mention pour la correction.

C est le quatrieme episode du meme mecanisme en deux jours, et le second de
la meme forme exacte : H11b avait reproche a H11 d avoir declare le defaut 74
ferme sur une mesure aveugle. Un chantier plus tard, j ai recommence sans
detecteur trop etroit pour m excuser : j ai ecrit "ferme" parce que j en
avais parle.

## Ce qui ferme reellement le defaut 67

`tests/mcp/js/` est supprime, repertoire compris. Treize kilo-octets qui
adressaient sept serveurs par des noms de fichiers n ayant jamais existe dans
ce depot, et codaient en dur un bucket n ayant jamais existe sur ce serveur.
Supprime plutot que repare : rien nulle part ne dependait d un resultat vert
de sa part, et le reparer aurait voulu dire reecrire un harnais parallele aux
suites Python qui, elles, tournent.

`mcp/package.json` lance desormais les deux vraies suites. `mcp/README.md` ne
renvoie plus a `tests/test_mcp.py`, qui n existait pas davantage que le reste.

## Un defaut introduit par H12, et corrige ici

Le guide ecrit par H12 annoncait `expect 80 passed` pour `tests/mcp`. Le meme
commit ajoutait cinq tests a la barriere et portait la suite a 85. **Le
document etait faux a la seconde ou il etait pousse.**

La barriere de H12 ne l a pas vu parce qu elle verifiait que les chemins
existent, pas que les nombres soient justes. Encore une mesure plus etroite
que son nom.

Un test compare desormais le chiffre annonce par le guide au nombre de tests
reellement declares sous `tests/mcp`. Il vaut 88 aujourd hui, et le
guide le dit.

## Ce qui n a deliberement pas ete mis sous garde

`tests/mediaman`. Le comptage statique des `def test_` y donne 492 quand
pytest en compte 495 : trois tests naissent ailleurs que d une declaration
litterale. Poser la meme barriere sur ce dossier produirait un chiffre qui
aurait l air d une mesure sans en etre une - exactement ce que ce depot
fabrique depuis deux jours. On s en abstient, et on dit pourquoi.

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 20 passed in 0.44s ============================== |
| `suite-mcp` | ============================= 88 passed in 39.89s ============================== |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 22.59s ======================= |

## Portee

Aucun service redemarre, aucun conteneur touche, aucune ecriture InfluxDB,
aucun identifiant lu. Trois fichiers supprimes, tous morts.

## Defauts

Fermes, cette fois par suppression et non par mention : 67, 80.
Ouverts par ce chantier : 84 (H12 a publie un compte de tests que son propre
commit invalidait - corrige ici).

Restent ouverts : 61, 62, 68, 69, 70, 71, 72, 73, 79 partiel, 82, 83.

## Ce que ce chantier ne prouve pas

Que je ne recommencerai pas. La barriere posee ici attrape une forme precise
de sur-affirmation : un compte de tests publie dans un document. Elle ne dit
rien des trente-deux autres defauts declares fermes dans `logs/latest.json`,
dont aucun ne porte de critere verifiable. Les relire un par un est un
chantier en soi, et il n a pas ete fait.
