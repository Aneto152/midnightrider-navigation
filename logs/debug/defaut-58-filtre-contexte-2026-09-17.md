# Defaut 58 - le filtre de contexte de racing.js

**Date** : 2026-09-17
**Chantier** : H8a
**Fichier corrige** : `mcp/servers/racing.js`
**Portee** : une ligne dans la requete Flux, plus le commentaire qui
l explique et la batterie de tests qui l empeche de repartir.

---

## 1. Le defaut

`get_historical_snapshot` pose quatre requetes Flux, une par fait :
latitude, longitude, vitesse et cap sur le fond. Chaque requete bornait la
fenetre temporelle, choisissait la mesure et le champ, puis prenait le
point le plus recent. Aucune ne disait **de quel bateau**.

InfluxDB ne contient pas que le Midnight Rider. Il contient aussi chaque
cible AIS recue. Le point le plus recent de la fenetre appartient donc au
dernier navire qui a ecrit, et le voilier n a aucune raison d etre celui-la.

## 2. La mesure

Sonde H7b v2, lecture seule, 27 requetes sur l InfluxDB de production,
2026-09-17. Fenetre de 300 s finissant a `2026-09-07T14:36:25Z`, soit
exactement ce que `racing.js` interroge avec `window_seconds: 300`.

| fait | requete ACTUELLE | requete CORRIGEE |
|---|---|---|
| latitude | 40.7759233 | 40.8357563 |
| longitude | -73.9419249 | -73.7122455 |
| speed_over_ground | 5.34 | 0 |
| course_over_ground | 3.4505 | 0 |

Contexte qui gagnait les quatre requetes :
`vessels.urn:mrn:imo:mmsi:368111560`, une cible AIS. Elle avait ecrit
apres nous dans la fenetre.

**Quatre faits sur quatre etaient ceux d un autre navire.** Le voilier
etait a l arret ; le systeme le declarait a 5,34 sur un cap de 3,4505.

## 3. Pourquoi le tag `self` suffit

| mesure | resultat |
|---|---|
| valeurs du tag `self` sur `navigation.position`, 365 j | `["true"]` et rien d autre |
| contextes portant `self=true` | 1 seul : `vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f` |
| contextes portant `self=false` | aucun : l etat de la requete est EMPTY |
| tag `self` present sur les 3 chemins interroges | oui, valeur `true` sur les trois |

Les 3990 contextes AIS ne portent **pas** de tag `self`. Ils ne portent
pas `self=false` : ils n ont pas le tag du tout. `r.self == "true"` les
exclut donc sans qu il faille enumerer quoi que ce soit.

Barriere de mesure executee par ce script avant toute ecriture : sur la
journee du 2026-09-07, le nombre de nos propres lignes est identique avec
et sans le filtre, sur les trois chemins. **Zero de nos lignes perdue.**

## 4. Le correctif

```
      |> filter(fn: (r) => r._field == "${selector.field}")
      |> filter(fn: (r) => r.self == "true")      <-- ajoute
      |> keep(columns: ["_time", "_value"])
```

### L ordre n est pas un detail

`keep(columns: ["_time", "_value"])` supprime **toutes** les autres
colonnes, dont le tag `self`. Le filtre place en dessous ne verrait plus
rien a filtrer : il laisserait passer tout le monde et retablirait le
defaut sans qu aucun test ne bronche. Le test
`test_le_filtre_self_est_envoye_et_precede_keep` compare les positions
des deux chaines dans la requete emise, pas seulement leur presence.

### Aucune source n est epinglee

Les trois chemins portent trois valeurs de tag `source` : `N2K.0`,
`N2K.1` et `N2K.2` (mesure du 2026-09-17 ; on en croyait deux). Les deux
Vulcan 7 ne sont pas toujours allumes ensemble. Preferer une source
nommee rendrait la collecte aveugle le jour ou cette source se taît.
`group()` puis `last()` prennent le point le plus recent, quelle que
soit la source qui l a ecrit. Le test
`test_aucune_source_n_est_epinglee` interdit toute regression sur ce
point.

## 5. Les tests

`tests/mcp/test_defaut_58_context_filter.py`, 6 tests. Ils lancent le
**vrai** `racing.js` contre un faux InfluxDB qui **lit** la requete Flux
recue et repond en consequence, comme le vrai moteur.

C est la difference avec le faux des tests existants, qui renvoie la meme
reponse quelle que soit la requete : ce faux-la ne pouvait pas voir la
difference entre une requete filtree et une requete qui ne l est pas.
C est pour cela que 911 lignes de tests de contrat ont laisse passer le
defaut 58.

| test | ce qu il interdit |
|---|---|
| `test_le_filtre_self_est_envoye_et_precede_keep` | filtre absent, ou place sous `keep()` |
| `test_la_cible_ais_plus_recente_est_ignoree` | publier la position d une cible AIS |
| `test_aucune_source_n_est_epinglee` | epingler `N2K.0/1/2` ou `sourcePriorities` |
| `test_les_quatre_faits_portent_l_heure_du_bateau` | melanger nos points et les leurs |
| `test_sans_cible_ais_le_resultat_est_identique` | casser le cas ou nous sommes seuls |
| `test_si_le_filtre_ne_rend_rien_le_snapshot_est_incomplet` | se rabattre sur une cible AIS quand nous manquons |

Repetition hors ligne avant livraison, sur une copie du depot a
`6c7bfa32` : **4 tests sur 6 echouent avant le correctif**, les 6 passent
apres. Les 2 qui passaient deja sont les deux tests de garde, ceux qui
interdisent une regression future.

## 6. Ce qui reste ouvert

- **Defaut 63, nouveau** : la cle publiee s appelle
  `course_over_ground_degrees` mais la valeur est celle stockee par
  Signal K, en **radians**. La cible AIS mesuree rendait 3,4505, ce qui
  ne peut pas etre des degres. Aucune conversion n existe dans
  `racing.js`. Corriger touche un contrat publie : arbitrage de Denis
  requis avant toute modification.
- **Jalon MediaMan du 2026-09-15** (`f79abaf5ba15`) : produit avec la
  requete fausse, donc invalide. A rejouer avec le code corrige.
- **Defaut 61** : `scripts/commit-logs.sh` commite l index entier.
  Correctif de 3 lignes propose, non applique, touche un service en
  fonctionnement.
- **Defaut 62** : tableau des unites de `etc/systemd/system/README.md`
  complete le 2026-09-17 mais la Deployment Checklist copie encore
  `*.service` en bloc.
- 18690 series pour `navigation.position` sur 365 jours : cardinalite a
  regarder un jour, sans urgence.

## 7. Cardinalite mesuree, pour memoire

| chemin | series sur 365 j | derniere ecriture |
|---|---|---|
| `navigation.position` | 18690 | 2026-09-07T14:36:24.298Z |
| `navigation.speedOverGround` | 3816 | 2026-09-07T14:36:24.297Z |
| `navigation.courseOverGroundTrue` | 3327 | 2026-09-07T14:36:24.297Z |
| `environment.wind.angleApparent` | 2 | 2026-09-07T14:36:24.135Z |

C est cette cardinalite qui rend `group()` indispensable avant `last()` :
sans lui, `last()` rend une ligne par serie et le code en choisissait une
au hasard.
