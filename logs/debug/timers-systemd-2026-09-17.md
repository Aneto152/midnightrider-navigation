# Minuteurs systemd de publication des journaux — constat du 2026-09-17

Etabli par `h7e-v1`. Toutes les valeurs ci-dessous sont mesurees sur
le Pi ou lues dans le depot, aucune n est supposee.

## 1. Deux minuteurs, un seul qui fonctionne

| Unite | Cadence | Etat mesure le 2026-09-17 |
|---|---|---|
| `midnight-logs-commit.timer` | 15 min | actif, fonctionne — auteur du commit `80f3980` |
| `midnight-logsync.timer` | 3 min | **desarme ce jour** ; declenchait une unite qui echouait a chaque fois |

## 2. midnight-logsync n a jamais rien fait

```
Active: failed (Result: exit-code)
Process: ... (code=exited, status=200/CHDIR)
midnight-logsync.service: Changing to the requested working directory failed:
    No such file or directory
```

`WorkingDirectory=/home/pi/midnightrider-navigation` n existe pas :
l utilisateur du bord est `aneto` et le depot est en
`/home/aneto/midnightrider-navigation`. systemd echoue **avant** de lancer
`bash`. Consequences :

- aucun journal n a jamais ete tronque par cette unite ;
- aucun commit n a jamais ete produit par elle ;
- environ **480 echecs par jour** dans le journal systemd, 18 ms chacun.

Le chemin `/home/pi/` est un vestige d avant la migration vers `aneto`.
`docs/DECISIONS/MEDIAMAN-HISTORICAL-DRY-RUN.md` le notait deja comme
obsolete : le constat etait juste, il n avait simplement pas ete suivi
d effet.

## 3. Pourquoi il ne faut PAS la reparer

Son `ExecStart` contient :

```bash
if [ "$size" -gt 900000 ]; then
  tail -300 "$f" > /tmp/_logtrim && cp /tmp/_logtrim "$f"
fi
```

Tout journal de plus de 900 ko serait **ecrase sur place** par ses 300
dernieres lignes, sans sauvegarde. L unite installee ne declare par
ailleurs **aucun `User=`** : elle tournerait en `root` dans un depot
appartenant a `aneto`. Enfin, elle commiterait et pousserait **toutes les
3 minutes**, soit le defaut 61 avec une fenetre cinq fois plus serree.

Cette unite a ete sauvee par son propre bug.

## 4. Ecart entre l unite installee et la copie du depot

La copie versionnee ne decrivait pas ce qui tournait. Elle est alignee
par ce commit, precedee d un bandeau de retrait.

### midnight-logsync.service

```diff
7d6
< User=pi
9a9,14
>  for f in logs/services/*.log; do \
>  size=$(wc -c < "$f" 2>/dev/null || echo 0); \
>  if [ "$size" -gt 900000 ]; then \
>  tail -300 "$f" > /tmp/_logtrim && cp /tmp/_logtrim "$f"; \
>  fi; \
>  done; \
```

### midnight-logsync.timer

_La copie du depot etait deja conforme._

## 5. Aucune fonction perdue — verifie, pas suppose

`scripts/commit-logs.sh` declare :

```bash
LOG_PATHS="logs/services/ logs/debug/ logs/latest.json logs/oc-actions.log"
```

Les quatre chemins que `midnight-logsync` pretendait publier y sont deja.
Le script de ce commit refuse de s executer si ce n est pas le cas.

## 6. Defaut 61 — cause racine, non corrigee ici

`scripts/commit-logs.sh` est irreprochable sur son `git add` : il
n ajoute que `logs/`. Le probleme est ailleurs :

| Ligne | Code | Probleme |
|---|---|---|
| 20 | `git add $LOG_PATHS` | correct, n ajoute que `logs/` |
| 22 | `git diff --cached --quiet` | teste l index **entier**, pas seulement `logs/` |
| 38 | `git commit -m "logs: auto-update — …"` | valide l index **entier** |

Un `git commit` emporte tout l index. Le 2026-09-17 a 21:51:02Z, l index
contenait le `git mv` laisse par `h7d-v2`, arretee sur son garde-fou sans
commiter : le job l a publie sous l identite
`MidnightRider AI Assistant <ai@midnightrider.local>`, message
`logs: auto-update —  4 files changed, 97 insertions(+), 2 deletions(-)`.

> **Rectification du 2026-09-17, chantier H8a.** Les deux citations
> ci-dessus - `LOG_PATHS` et ce message de commit - avaient ete
> ecrites de memoire et etaient fausses : mauvais ordre pour la
> premiere, `43 insertions` au lieu de `97` pour la seconde. Elles
> ont ete remplacees par les chaines relues, l une dans
> `scripts/commit-logs.sh` ligne 17, l autre par l API GitHub sur le
> commit `80f3980912be16616f300017ca00d76e5be90617`. La demonstration
> de la section 5 n en depend pas : les quatre chemins sont les memes
> quel que soit leur ordre.

La barriere anti-secrets n a rien vu, et elle avait raison : un
renommage ne contient pas de secret.

Le meme mecanisme avait publie l autorisation InfluxDB de
`SEC-2026-09-14-01`.

Correctif propose, **non applique dans ce commit** — il touche un service
de production et demande ta validation :

```bash
# avant le git add, refuser de publier le travail d autrui
HORS_LOGS="$(git diff --cached --name-only | grep -v '^logs/' || true)"
if [ -n "$HORS_LOGS" ]; then
  echo "index non vide hors logs/, desindexation :" >&2
  echo "$HORS_LOGS" >&2
  git reset -q -- $HORS_LOGS
fi
# et restreindre le test de l etape suivante
git diff --cached --quiet -- $LOG_PATHS && exit 0
```

## 7. Defaut 62 — le README du dossier systemd n est pas a jour

Mesure du jour dans `etc/systemd/system/` :

- **15** unites presentes ;
- **9** citees par le tableau *Services* ;
- **5** citees mais inexistantes au depot ;
- **11** presentes mais jamais citees.

Detail dans `etc/systemd/system/README.md`. La remise a plat exige de
confronter chaque unite a ce qui est reellement installe sur le Pi :
chantier distinct, non fait ici.

## 8. Ce que ce commit ne fait pas

- il ne modifie aucun service en fonctionnement ;
- il ne corrige pas `scripts/commit-logs.sh` (defaut 61) ;
- il ne remet pas a plat le tableau du README (defaut 62) ;
- il ne supprime aucun fichier : `midnight-logsync` reste versionnee,
  desarmee et documentee, retablissable en une commande.
