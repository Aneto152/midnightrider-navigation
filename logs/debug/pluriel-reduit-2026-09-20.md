# Le pluriel reduit au singulier

**Chantier** : h14d-v1
**Base** : 80462e958337e7faaf440b26e5f769a7041a6b22
**Commit de contenu** : 9e4ae872d9d88306c5758776b0c3e19cf7108f32

## Ce que H14c a ecrit

> - **97** est ouvert : les quatre conteneurs de production sont definis
>   hors depot, et le depot porte une seconde definition des memes services
> - **98** est ouvert si le projet proprietaire n est pas celui du depot

Et dans son message de commit : *97 et 98 ouverts, avec constat*.

## Ce que la mesure dit, un conteneur a la fois

| Conteneur | Projet proprietaire | Etat |
|---|---|---|
| `influxdb` | `midnightrider-navigation` | running |
| `grafana` | `midnightrider-navigation` | running |
| `regatta` | `midnightrider-navigation` | running |
| `start-line-worker` | `workspace` | running |

Projet compose du depot : `midnightrider-navigation`, confirme par les etiquettes des
conteneurs qu il definit. Conteneurs dont le nom est fixe par
`docker-compose.yml` : 4. Dont la definition ne vient pas de ce
fichier : 1. Dont le proprietaire est un autre projet compose :
1.

Un seul conteneur est defini hors depot, pas quatre. Et le defaut 98 n a
pas ete ouvert du tout : la sortie de H14c porte
`PROJET_PROPRIETAIRE_DES_CONTENEURS=midnightrider-navigation` et
`DEFAUTS_OUVERTS=25`.

## La cause

Une variable au singulier pour quatre conteneurs :

```
PROJET=$(docker inspect -f '{{index .Config.Labels "..."}}' influxdb)
```

Le premier conteneur de la liste appartient au depot. Trois sur quatre
lui ressemblent. La variable a pris cette valeur, la condition
d ouverture de 98 l a comparee au projet du depot, et elle est tombee du
mauvais cote. Les textes, eux, etaient ecrits d avance : ils ne
dependaient d aucune mesure.

Quatorzieme fois cette semaine qu une mesure est plus etroite que son
nom. La premiere par reduction d un pluriel :

| # | Ou | Disait | Mesurait |
|---|---|---|---|
| 12 | H14c | le projet proprietaire des conteneurs | le projet du premier conteneur |
| 13 | le defaut 92 | ce fichier declare un Signal K | une etiquette de conteneur le mentionne |
| 14 | mon banc d essai | la barriere echoue sur un clone propre | elle echoue hors arbre git |

## Le defaut 98 est reel

Le depot fixe `container_name` pour chacun de ses quatre services. L un
de ces noms est deja porte par un conteneur d un autre projet compose.
Un `docker compose up -d` lance depuis le depot - c est ce que prescrit
`docs/ops/RECOVERY-GUIDE-SAFE.md` section 1.2, en situation de panne -
s arreterait sur un conflit de nom.

Le guide porte desormais le tableau des proprietaires, l avertissement,
et la commande de controle a passer avant.

## Ce que ce chantier repare

- le defaut **97** est reecrit sur la mesure, un conteneur a la fois
- le defaut **98** est ouvert, avec son constat
- les deux lignes fausses du compte rendu de H14c sont rectifiees, le
  texte d origine cite dans le bloc de rectification
- trois retractations sont ajoutees a `logs/debug/RETRACTATIONS.md`,
  dont une qui est de moi : le trou de `config/wifi-ap.txt` n a jamais
  existe
- `chemins_morts()` consulte git comme `chemins_cites()` le faisait
  deja ; l exception codee en dur est retiree

## La mesure nouvelle

Un compte rendu qu un defaut cite comme sa preuve ou son constat est
invoque pour l etat d aujourd hui. Il doit donc dire l etat
d aujourd hui, et jamais sous condition. Les comptes rendus que plus
rien ne cite sont de l histoire : ils sont hors de cette mesure, et le
code le dit. Une phrase fausse survit a un seul endroit, la citation.

Quatre controles de plus : la barriere passe de 44 a 48,
`tests/mcp` de 112 a 116.

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 48 passed in 0.87s ============================== |
| `suite-mcp` | ============================= 116 passed in 39.98s ============================= |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 22.11s ======================= |

## Ce que ce chantier n a pas fait

Aucun geste sur la machine. Aucune ecriture dans InfluxDB. Le conteneur
`start-line-worker` n a pas ete touche, le fichier compose hors depot non
plus : le defaut 98 dit ce qu il faut savoir avant d y toucher, et rien
n a ete decide ici.
