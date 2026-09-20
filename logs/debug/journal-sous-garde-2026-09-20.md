# Le journal sous garde : reparer l intention, pas seulement l ecriture

**Chantier** : h12c-v1
**Base** : 9234a33a149ec969f1b5c2e47f55c7369f50e0bc
**Commit de contenu** : cbd002bbe5e6789a0d8d64cbf17fb5eb39b407cc

## Ce que la verification de H12b a trouve

H12b a ferme le defaut 67 correctement : le harnais mort supprime, `npm
test` repare, `mcp/README.md` corrige, tout verifie par l API. Le travail
etait juste. Le registre qui en rend compte ne l etait pas.

| Incoherence | Etat au commit 9234a33a |
|---|---|
| defaut 67 | present dans `defects_closed` **et** dans `defects_open` |
| defaut 74 | declare ferme deux fois, par H11 puis par H11b |
| une entree fermee | sans identifiant, donc invisible a tout recoupement |
| tests portant sur ces listes | zero |

## D ou vient la premiere

Elle est de ma main, et d une espece qui merite d etre nommee. En relisant
le script H12b avant de le livrer, j ai vu une ligne `ouverts[:] = [...]`
qui devait retirer le defaut 67 de la liste des ouverts. Je l ai jugee sans
effet et je l ai supprimee.

Elle n etait pas sans effet. Elle etait **mal ecrite**. J ai efface
l intention au lieu de reparer l execution, et le journal se contredit
desormais sur la ligne meme ou il reprochait a H12 de se contredire.

Une relecture qui supprime ce qu elle ne comprend pas ne vaut pas mieux
qu une absence de relecture.

## Et la sixieme mesure trop etroite

En comptant ces incoherences, j ai d abord annonce **trois** entrees sans
identifiant. Il y en a **une**.

Mon motif etait `\d+\b`. Applique a `20b le compte administrateur Grafana
n etait detenu par personne`, il echoue : apres `20` vient `b`, deux
caracteres de mot, donc pas de frontiere. L entree etait declaree orpheline
alors qu elle porte un sous-identifiant parfaitement legitime.

C est la sixieme fois cette semaine qu une mesure porte un nom plus large
que ce qu elle regarde. Les cinq precedentes :

1. H11 : `INFLUX(?:DB)?_` ne voyait pas `INFLUX_DB_`
2. H12 : le detecteur de chemins ne lisait que les accents inverses
3. H12 : un defaut declare ferme parce que le guide en parlait
4. H12 : `expect 80 passed` dans un commit qui portait la suite a 85
5. Le diagnostic du 2026-09-20 : un comptage InfluxDB filtrant sur un champ
   `value` la ou la position s ecrit en `lat` et `lon`

Le motif retenu ici est `^\s*(\d+[a-z]?)\b`, et deux tests d echantillon
exigent qu il voie `20b` comme un identifiant et `ProtectHome...` comme une
orpheline. La difference entre affirmer qu une mesure voit et le prouver
est tout le sujet de la semaine.

## Ce que fait ce chantier

| Action | Effet |
|---|---|
| `defects_open` | l entree 67 retiree : H12b l a ferme par suppression |
| `defects_closed` | les deux entrees 74 fusionnees en une, sans perdre le fait que la premiere fermeture reposait sur un detecteur aveugle |
| `defects_closed` | la fermeture `ProtectHome` recoit le numero 86, marque comme retroactif |
| barriere | quatre controles nouveaux sur le journal, deux echantillons qui prouvent qu ils rendent rouge |
| guide de secours | 88 -> 94 tests annonces, aux deux endroits |

Le passage de 88 a 94 n est pas une retouche cosmetique : c est la
garde posee par H12b sur les comptes annonces qui l a **impose**. Ajouter
six tests sans corriger le guide aurait fait echouer la suite. Une barriere
qui gene est une barriere qui fonctionne.

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 26 passed in 0.48s ============================== |
| `suite-mcp` | ============================= 94 passed in 40.23s ============================== |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 21.92s ======================= |

La barriere est relancee une seconde fois apres l ecriture des journaux,
parce que cette ecriture modifie precisement le fichier qu elle surveille.
Poser une garde sur un fichier puis le modifier sans reverifier serait la
meme faute sous un autre habit.

## Portee

Aucun service redemarre, aucun conteneur touche, aucune ecriture InfluxDB,
aucun secret manipule. Trois fichiers de contenu, trois de journal.

## Defauts

- **85 ouvert et ferme ici** : le journal se contredisait sur trois points
  et rien ne le verifiait.
- **86 attribue retroactivement** a une fermeture qui n avait pas de numero.

## Ce que ce chantier ne prouve pas

Il ne dit rien de la **justesse** des trente-trois fermetures declarees. Il
verifie qu elles sont coherentes entre elles, pas qu elles sont vraies. Le
defaut 67 a montre qu une entree peut etre parfaitement bien formee et
entierement fausse. Cet audit reste a faire, et reste non fait.

Il ne dit rien non plus de l etat du bord, mesure le meme jour : aucun
peripherique serie, aucune interface CAN, les trois daemons BLE eteints,
Signal K ne tenant que deux chemins sans rapport avec la navigation, et
aucun point de position dans InfluxDB depuis le 7 septembre.

---
*Ecrit par H12c le 2026-09-20T18:31:32.*
