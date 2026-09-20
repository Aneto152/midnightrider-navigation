# Une fermeture doit porter sa preuve

**Chantier** : h13-v1
**Base** : f795d2e8b067d140c6a25bf498c13ee9dc0f4221
**Commit de contenu** : cfb5201b633d8a026ab79a876e0849577f3bcc17

## Ce que l audit a trouve

Vingt des trente-quatre fermetures declarees ont ete passees a la preuve
materielle : non pas leur texte, l etat du depot au commit f795d2e8.

| Verdict | Nombre |
|---|---|
| prouvees | 19 |
| fermee a moitie | 1 (defaut 45) |
| hors de portee d une preuve | 14 |

Les quatorze ne sont pas douteuses. Elles sont **infalsifiables par
construction**. Dix disent `corrected by addition` : un paragraphe a ete
ajoute a un compte rendu passe. Rien dans le depot ne peut les confirmer,
rien ne peut les refuter.

C est le vrai resultat, et il est plus interessant que le decompte :

> Le registre ne distingue pas ce qui a change dans le systeme de ce qui a
> ete ecrit a propos du systeme. Une ligne de code corrigee et une note
> ajoutee a un rapport y occupent la meme place, avec le meme statut de
> ferme.

## Ce que ce chantier change

Chaque entree de `defects_closed` porte un suffixe ` | preuve: `. Vingt en
citent une materielle - un fichier, un test, une ligne. Quatorze avouent
n en avoir aucune, et le disent dans les termes exacts.

Trois controles nouveaux, plus un quatrieme sur le contrat historique :

| Controle | Ce qu il refuse |
|---|---|
| marqueur de preuve | une fermeture qui ne dit pas ce qui la prouve |
| existence des chemins | une preuve qui cite un fichier inexistant |
| cliquet a 14 | qu une quinzieme fermeture sans preuve apparaisse |
| contrat historique | un en-tete en desaccord avec sa propre enumeration |

Le cliquet est la piece qui compte. Le plafond peut **descendre**, quand
une vieille fermeture recoit enfin une preuve. Il ne remonte pas.

## Les deux defauts corriges

**87** - `tests/mcp/test_phase2_historical_contract.py` annoncait
`Covers 23 scenarios:` puis enumerait vingt-quatre points. H5a avait
aligne le nombre sur le compte des fonctions et laisse intacte la liste
que ce nombre resume. L en-tete annonce desormais ses deux chiffres, et un
test les compare a la realite du fichier.

**88** - `etc/systemd/system/mediaman-events.service` affirmait en
commentaire que `mediaman.service` declare `ProtectHome=yes`. C est faux
depuis H5d : les deux unites declarent `no`. Un commentaire qui decrit un
etat revolu au present est un piege pour le prochain lecteur.

## Ce que je n affirme pas

Sur le defaut 87, j ai tente d apparier les vingt-quatre scenarios aux
vingt-trois fonctions de test. **L appariement n est pas fiable** : huit
scenarios et sept fonctions restent sans correspondance evidente. Je ne
sais donc pas si un scenario est reellement decouvert. Je corrige ce qui
est prouvable - l accord de l en-tete avec sa propre liste - et je
m abstiens sur la couverture.

## Et mon detecteur s est trompe trois fois sur quatre

L audit a leve quatre alertes. Trois etaient fausses :

| Alerte | Ce que je lisais | Ce qui etait ecrit |
|---|---|---|
| 38 | renvoi vers un fichier absent | une phrase qui documente cette absence |
| 86 | ProtectHome=yes toujours la | la directive vaut `no`, les `yes` sont des commentaires |
| 74 | onze references au bucket signalk | deux mentions historiques, et `signalk-cloud`, un bucket different |

La derniere merite d etre nommee. Mon motif etait `signalk\b`, et le tiret
de `signalk-cloud` est une frontiere de mot. **Septieme mesure fautive de
la semaine - la premiere qui peche par exces plutot que par defaut.** Six
jours a elargir des detecteurs trop etroits, et celui-ci, trop large,
aurait accuse a tort trois fermetures honnetes si je l avais cru sur
parole.

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 32 passed in 0.51s ============================== |
| `contrat-historique` | ============================= 23 passed in 19.95s ============================== |
| `suite-mcp` | ============================= 100 passed in 39.99s ============================= |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 22.04s ======================= |

La barriere est relancee apres l ecriture des journaux, parce que cette
ecriture modifie le fichier qu elle surveille.

## Portee

Aucun service redemarre, aucun conteneur touche, aucune ecriture InfluxDB,
aucun secret manipule. Cinq fichiers de contenu, trois de journal.

## Ce qui reste, et que ce chantier ne touche pas

- le bord est aveugle : aucun peripherique serie, aucun CAN, trois daemons
  BLE eteints, et aucun point de position dans InfluxDB depuis le 7
  septembre
- le token InfluxDB SEC-2026-09-14-01 n est toujours pas revoque
- `telegraf.service` est en echec, le conteneur `signalk` est sorti il y a
  quatre mois
- trois des quatre timers documentes sont introuvables sur la machine, et
  je n ai pas tranche entre leur disparition et un releve trop etroit
- `.git` pese 344 Mo

---
*Ecrit par H13 le 2026-09-20T18:53:03.*
