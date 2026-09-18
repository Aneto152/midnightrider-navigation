# La chaine d ingestion est au repos, pas cassee

**Chantier** : h11-v1
**Parent** : d5bba0054b9e49aa64d28c9b3674a3ccf64f0f75
**Commit de contenu** : 0d4b94a509be2b3fd06fca4f0134b82934060665
**Diagnostic execute le** : 2026-09-18T21:51:16Z

## La question

`logs/latest.json` portait depuis H9 la mention *aucune donnee ingeree depuis
2026-09-07T14:36:24Z*. Onze jours de silence. La question etait de savoir si
c etait une panne.

## La reponse : non

Denis a confirme que le 7 septembre etait la derniere sortie et que le panneau
electrique du bord est coupe depuis. Tout ce que le diagnostic a releve est la
consequence normale de cet etat.

| Maillon | Etat mesure | Lecture |
|---|---|---|
| Bus N2K | aucune interface CAN, aucun `/dev/serial/by-id`, aucun processus NMEA | passerelle alimentee par le bus, bus eteint |
| Signal K | `active`, `NRestarts=0`, depuis le 2026-09-15 16:25 EDT | fonctionne |
| Arbre `vessels` | `GET /signalk/v1/api/vessels` rend 2 octets, soit `{}` | rien n est jamais entre |
| Plugin d ecriture | `enabled: true`, url, org, bucket et jeton corrects | correct, mais rien a ecrire |
| InfluxDB | `status: pass`, v2.8.0, jeton accepte (HTTP 200) | en bon etat |
| Donnees | dernier point 2026-09-07T13:42:57Z ; 0 sur 7 j, 263 sur 30 j | s arrete a la derniere sortie |

Le Pi a redemarre le **2026-09-14 a 21:52**, soit une semaine apres l arret des
donnees. Le redemarrage n y est pour rien.

`docs/SIGNALK-PLUGINS-INVENTORY.md` l. 408 notait deja `signalk-um982-gnss`
comme *enabled, device absent, materiel NON CONNECTE au 2026-09-17*.

**Consequence pour H10** : les seuils de detection d evenements devront etre
mesures sur l historique deja enregistre - juillet et debut septembre - et non
sur des donnees vivantes. C est faisable hors ligne et sans attendre la
prochaine sortie.

## Erreur de jugement, cote assistant

Cet arret avait ete classe au-dessus de H10 dans l ordre des priorites, sous
le libelle *onze jours sans ingestion*. Une absence de donnees etait traitee
comme une panne sans que la question *le bateau a-t-il navigue* ait ete posee.
Elle tenait en une ligne et aurait du preceder l execution du diagnostic.

## Ce que le diagnostic a trouve en passant

C est la vraie recolte. Aucun de ces points n a de rapport avec l ingestion.

| Defaut | Constat | Preuve |
|---|---|---|
| 69 | conteneur Docker nomme `signalk`, `Exited (137)` depuis 4 mois | `docker ps -a` |
| 70 | `midnight-logsync.service` en echec : les journaux de service ne remontent plus sur GitHub | `systemctl list-units --state=failed` |
| 71 | `telegraf.service` en echec, et cette unite n existe nulle part dans le depot | idem |
| 72 | quatre plugins de calcul tournent a vide et ont ecrit 11,8 Mo de journaux | `ls -lt logs/services/` |
| 73 | InfluxDB 2.8.0 panique cote lecture sur l operateur `last` | `docker logs influxdb` |
| 74 | six commandes de la documentation visent un bucket inexistant | corrige par H11 |

Le defaut 69 merite un mot : la regle numero un du bord est *Signal K se pilote
par systemctl, jamais par docker*, et il existe un conteneur qui porte ce nom,
mort depuis quatre mois, pret a etre relance par qui lira `docker ps -a`.

Le defaut 73 est le plus preoccupant pour la suite :

```
msg="Dispatcher panic" error="panic: arrow/array: index out of range"
source="@1:240-1:260: last"
```

Des dizaines d occurrences le 2026-09-17 a 03:27, toutes sur `last` - l operateur
sur lequel reposent les deux portes de H9 et sur lequel H10 s appuiera davantage.

Le defaut 72 en chiffres, releves a la minute du diagnostic :

```
j30-leeway-calc.log    3,8 Mo
truewind-calc.log      3,1 Mo
current-calc.log       2,2 Mo
heading-true-calc.log  2,6 Mo
```

Le standard de journalisation fixe 5 Mo avec trois rotations. Deux de ces
fichiers en sont a mi-chemin, en bruit pur, sans aucune donnee d entree.

## Ce que H11 corrige

| Fichier | Ce qui etait ecrit | Ce qui est vrai |
|---|---|---|
| `docs/setup/INFLUXDB-CONFIG.md` l. 41, 70, 88, 117 | `INFLUX_BUCKET=signalk`, `from(bucket:"signalk")` | `midnight_rider` |
| `docs/ops/RECOVERY-GUIDE-SAFE.md` l. 183 | bucket `signalk` et measurement `navigation` | `midnight_rider`, `navigation.position` |
| `README.md` l. 272-273 | org `midnight-rider`, bucket `midnight-rider` | `MidnightRider`, `midnight_rider` |
| `docs/DATA-SCHEMA-MASTER.md` l. 353 | note ISSUE de mai 2026 + renvoi mort | rectification datee |
| `plugins/signalk-truewind-calculator.js.bak.v103` | fichier de sauvegarde orphelin | supprime |

## La barriere, elargie

`tests/mcp/test_h9b_coherence_doc_code.py` verifiait les chemins cites. Elle verifie desormais aussi les
**valeurs** : tout nom de bucket ou d organisation cite dans la documentation
doit etre celui qui existe, sauf sur une ligne de citation commencant par `>`,
et sauf pour une courte liste de gabarits ou chaque entree porte sa raison.

Elle a ete executee sur le depot avant correction : **trois tests sur neuf
echouent**. Le comptage manuel avait trouve deux occurrences fautives ; la
barriere en a trouve six, plus une organisation. C est precisement pour cet
ecart qu elle existe.

## Tests

| `barriere` | ============================== 9 passed in 0.20s =============================== |
| `suite-mcp` | ============================= 77 passed in 39.55s ============================== |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 21.75s ======================= |

## Ce que H11 n a pas fait

Aucun service n a ete touche. Le conteneur zombie, les deux unites en echec et
le bavardage des quatre plugins demandent une action sur l etat du systeme et
attendent une validation explicite.
