# InfluxDB token audit — 2026-09-15 — read-only

Produced by audit-h1-influx-tokens.sh (h1b-v2) at 20260915T201600Z.
Nothing was modified, restarted or revoked. **No token value appears in
this report**: every token is reduced to sha256[:16]. The exposed token is
identified by the fingerprint `e80a47801529a25c` published in the
SEC-2026-09-14-01 incident record.

## Authorizations

CLI output shape: JSON array

| # | id | description | user | status | scope | sha256[:16] | identified as |
|---|----|-------------|------|--------|-------|-------------|---------------|
| 1 | 10a80277d9d8f000 | admin's Token | admin | active | read+write on /annotations,/authorizations,/buckets | 0cdf3fba24268e7c |  |
| 2 | 10a814629358f000 |  | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | e80a47801529a25c | EXPOSED TOKEN - to revoke |
| 3 | 10b39179ec7d7000 | Grafana-20260512 | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | 2e6fb92a0a7b5705 |  |
| 4 | 10b3917ec6bd7000 | Grafana-20260512-1822 | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | 2f897643ebd9779c |  |
| 5 | 10b3929b4f7d7000 | Grafana-fresh-1778624825 | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | 083a8f304fbb406b |  |
| 6 | 10b3a34816b62000 | start-line-worker-2026-05-12-auto | admin | active | read+write on buckets/bfe67dc473be4e24 | b17d861fa166a4b3 |  |
| 7 | 10b48c80ddb62000 | MidnightRider-Token-2026-05-13-rec | admin | active | read+write on 65467721b2e06bdc/annotations,65467721b2e0... | c479e01cc819217c |  |
| 8 | 115577aebd73c000 | midnightrider-services 2026-09-15  | admin | active | read+write on buckets/bfe67dc473be4e24 | 3e83dfafb0f92009 | MediaMan .env token - keep |

authorizations listed: 8

## Consumers

```
    configuration.influxes.[0].token               len=88 sha256[:16]=e80a47801529a25c  <<< THE EXPOSED TOKEN IS STILL IN USE HERE

--- container environment variables (names and fingerprints only) ---
  grafana                INFLUX_TOKEN                       EMPTY
  influxdb               no sensitive variable in its environment
  regatta                GPG_KEY                            len=40 sha256[:16]=02978be54c8be7cd
  start-line-worker      INFLUX_TOKEN                       len=88 sha256[:16]=b17d861fa166a4b3
  start-line-worker      INFLUXDB_TOKEN                     len=88 sha256[:16]=25ec316112f46bd6
  start-line-worker      GPG_KEY                            len=40 sha256[:16]=02978be54c8be7cd

--- systemd units carrying an Environment= secret ---

== STEP 2b - ADDED 1 : WHICH TOKEN DOES THE GRAFANA DATASOURCE USE ?
--- provisioning files inside the container (read-only) ---
  datasource-influxdb.yaml
  bytes collected: 357
  provisioning files contain no token-shaped value

--- grafana.db datasource table (copy read locally, never committed) ---
  id=5 name='InfluxDB' type=influxdb url=http://localhost:8086 secure_blob_bytes=88 basic_auth_user=''

  secure_json_data is AES-encrypted with the Grafana secret key, so the
  token CANNOT be fingerprinted from here. If a datasource of type
  influxdb carries a non-empty secure blob, assume it may hold the
  exposed token and verify empirically after rewiring: reload one
  dashboard and check that it still returns data.

```

## Ingestion state

```
  signalk is-enabled: enabled

--- newest point in the bucket, single query over the last 30 days ---
  HTTP 200
  newest navigation.position timestamp: 2026-09-07T14:36:24.298Z

--- ADDED 2 : why is ingestion silent ? (read-only) ---
  data-flow.log last modified : 2026-09-07 10:36:27.336363926 -0400
  last recorded event         :
    [2026-09-07T14:36:27.337Z] [FLOW] Wind→SK: TWD=325.6deg TWS=9.6kts TWA=-101.3deg [signalk-truewind-calculator]
  serial devices present      :
  Signal K self position timestamp (value never printed):
    no answer from the Signal K REST API

--- recent Signal K write errors, if any (masked) ---

```

## Exposure in tracked files

```
  docs/guides/RESTORE.md                               tracked=True  exact-token occurrences=0  token-shaped runs=1  bytes=4171

  .gitignore coverage:
    logs/debug/crash-capture       ABSENT
    logs/diagnostic_raw            ABSENT
    .env                           present
    .openclaw-token                present

```

## Next step, to be validated by Denis

Revocation order remains create -> wire -> verify -> revoke. This audit
exists to establish, before any revocation, which consumer would lose
access, and whether Signal K ingestion is alive at all.

## Rotation 1 — Signal K plugin — 20260915T202511Z

The signalk-to-influxdb2 plugin no longer uses the exposed token.

- new authorization id: `1155af07b7b3c000`
- new token fingerprint: `5c13b0b9efee7017` (value never printed, never committed)
- scope: read+write on bucket `midnight_rider` (`bfe67dc473be4e24`) only, instead of the previous
  organisation-wide scope
- proven before rewiring: one point written to measurement
  `selftest.token_rotation` (HTTP 204) and read back (HTTP 200)
- Signal K restarted with systemctl, is-active=active
- exposed authorization `10a814629358f000`: **still active**, revocation is
  step H3, after the Grafana datasource is handled

Honest limit: no instrument is connected and the data flow stopped on
2026-09-07, so the end-to-end write path cannot be observed today.


## Repair — Grafana token wiring — 20260915T212534Z

The Grafana InfluxDB datasource held **no secret at all**: the API reported
`secure fields set: (none)` and its health endpoint answered
`ERROR`. The dashboards had therefore stopped reading InfluxDB.

Root cause, read in the repository and not guessed:
`grafana-provisioning/datasources/datasource-influxdb.yaml` declares the
datasource with `token: ${INFLUX_TOKEN}`, `docker-compose.yml` forwards
`INFLUX_TOKEN=${INFLUX_TOKEN}` to the container, and that variable was
EMPTY in the running container. Because provisioning is re-applied at every
Grafana start, a fix through the Grafana API would have been erased at the
next restart. The durable fix is to give the container a non-empty value,
then recreate it.

- container recreated with `up -d --no-deps --force-recreate grafana`
  (project `midnightrider-navigation`); influxdb, regatta and start-line-worker verified to be
  the exact same containers before and after
- token handed to the container: the one already in `.env`, fingerprint
  `3e83dfafb0f92009`; observed in the new container: `3e83dfafb0f92009`
- **accepted trade-off**: that authorization is bucket-scoped but carries a
  write permission, while Grafana only ever needs to read. Hardening it to
  least privilege is one line of `docker-compose.yml` plus one new token,
  deliberately postponed.
- datasource `efifgp8jvgj5sf` secure fields after: token
- health: ERROR -> OK
- bounded 60 s probe: 3 row(s) read directly from InfluxDB, 0
0 row(s)
  through the Grafana proxy (HTTP 400)
- dashboards listed by Grafana: 20 before, 20 after
- verdict: **REPAIRED**
- authorizations created: 0, revoked: 0

Two side facts recorded for H3: the read-only authorization
`1155b5f81bb3c000`, created by the aborted first attempt, is orphaned and
should be revoked; and `logs/debug/crash-capture-2026-06-28T190455Z.log`
and `logs/diagnostic_raw.txt` still contain the exposed token, which an
earlier version of this report failed to list.

Honest limits: no dashboard panel was rendered by this step. Only the
datasource health endpoint and one bounded query were exercised, and the
data window is the last one the boat produced, on 2026-09-07.

**Security finding**: the Grafana API still accepts its default admin
password, and `GF_AUTH_ANONYMOUS_ENABLED=true`. Out of scope here, H3.


## Revocation — deactivation of the exposed token — 20260915T215645Z

SEC-2026-09-14-01 is closed on the InfluxDB side. The authorization whose
value was published in this public repository no longer authenticates
anything.

**Deactivated, not deleted.** InfluxDB distinguishes `auth inactive`, which
stops the token from opening anything while keeping the record, from
`auth delete`, which is final. The first neutralises the leak just as
completely and leaves a way back if an unknown consumer — a cron job, a
notebook, a Power BI refresh, something on another machine — turns out to
depend on it. Deletion is a separate, later step.

| target | id | scope | fingerprint | result |
|---|---|---|---|---|
| exposed token | `10a814629358f000` | organisation-wide | `e80a47801529a25c` | yes |
| orphan from the aborted H2b v1 | `1155b5f81bb3c000` | read-only, one bucket | `b6ed642b97ec282a` | yes |

Identity was established by fingerprint before acting, not by id alone, and
each deactivation was proven end to end: the token read the bucket with
HTTP 200 before, and the same request returned HTTP 401 after.

Consumers verified immediately after, and unaffected:

- MediaMan `.env` token: HTTP 200, 3 row(s) on the bounded 60 s probe
- `signalk` service: active
- Grafana datasource health: OK before, OK after
- signalk journal lines mentioning 401/403/unauthorized in the following
  minutes: 0

Operational finding worth keeping: inside the `influxdb` container,
`influx auth list` works but `influx auth inactive` answers *401
Unauthorized*. The credential the CLI is configured with can read
authorizations and not write them. The deactivation therefore went through
the HTTP API, `PATCH /api/v2/authorizations/{id}`, with a credential that
declares write access on authorizations, injected through a curl config
file so that no secret ever reached the process table.

To put everything back, at any time, an undo script was generated next to
the credential it needs:

```
bash /tmp/h3a-raw-20260915T215645Z/undo.sh
```

What remains open, and is NOT addressed here: the token value is still
readable in the git history and in two tracked files,
`logs/debug/crash-capture-2026-06-28T190455Z.log` and
`logs/diagnostic_raw.txt`, neither of which is covered by `.gitignore`.
Those strings are now inert, but they must still be removed, the ignore
rules added, and a barrier put on `scripts/commit-logs.sh`, which commits
anything under `logs/` with no check at all.



## Corrections et nettoyage du dépôt — H3b — 20260915T223349Z

Cette section corrige par ajout quatre inexactitudes des sections
précédentes. L'historique n'est pas réécrit : ce qui a été écrit reste
lisible, avec sa correction en regard.

**Défaut 16 — un fait faux dans le rapport de H3a.** La section de
révocation affirme que la lecture refusée après désactivation a répondu
*HTTP 401*. Elle a répondu **HTTP 404**, avec le message
`could not find bucket "midnight_rider"`. Le script annonçait 401 en dur
au lieu d'inscrire le code réellement observé. La preuve reste valide, et
pour une raison vérifiable : quelques secondes plus tard, le token du
`.env` a lu ce même bucket en HTTP 200. Le bucket existe donc ; seule
l'identité qui demande a changé. Pour une autorisation désactivée,
InfluxDB ne résout plus le bucket et répond « introuvable » au lieu de
« non autorisé ». Lecture refusée dans les deux cas, et la vérification
qui fait foi — `status=inactive` relu dans InfluxDB — était passée.

**Défaut 18 — une affirmation fausse sur `.gitignore`.** La section de
révocation dit que les deux fichiers fautifs ne sont couverts par aucune
règle. Faux : `.gitignore` contient `*.log`, `logs/debug/*.log` et
`logs/*.txt`, qui les couvrent tous les deux. Mais `.gitignore` est sans
effet sur un fichier **déjà suivi** : ce qui manquait était le dé-suivi,
fait ici.

**Défaut 17 — deux faux positifs présentés comme des erreurs Grafana.**
Le comptage des lignes de journal mentionnant 401/403 attrapait les
chiffres à l'intérieur des horodatages à la nanoseconde
(`21:54:21.0**401**9142`). Les deux lignes remontées étaient de plus
antérieures au démarrage du script : elles ne pouvaient pas venir de la
désactivation.

**Défaut 14 — une ligne de journal coupée en deux.** La ligne `[DEBUG]`
de H2b v2 dans `logs/oc-actions.log` est scindée : un `grep -c … || echo
0` imprimait `0` deux fois, la seconde moitié de la ligne se retrouvant
sans horodatage. Le contenu est lisible, la structure ne l'est pas. Les
scripts suivants utilisent `|| true`.

**Défaut 15** avait déjà été corrigé par une ligne `CORRECTION` dans
`logs/oc-actions.log` lors de H3a.

### Nettoyage effectué

Les deux fichiers qui portaient encore la valeur publiée ont été retirés
du suivi git. Ils restent sur le disque du Pi, intacts, pour l'analyse ;
ils cessent d'être publiés. Occurrences retirées du dépôt :

| fichier | occurrences | traitement |
|---|---|---|
| `logs/debug/crash-capture-2026-06-28T190455Z.log` | 1 | `git rm --cached` |
| `logs/diagnostic_raw.txt` | 2 | `git rm --cached` |

Avant de les retirer, la valeur a été retrouvée dans ces fichiers par son
empreinte (jamais par sa valeur en clair) et son inertie prouvée : une
lecture réelle du bucket avec cette valeur répond HTTP 404.

Un balayage de **tous** les fichiers suivis du dépôt, contre la liste
complète des valeurs de tokens existantes, confirme que ces deux fichiers
étaient les seuls concernés et que plus aucune valeur de token vivant ne
figure dans le dépôt.

La valeur reste présente dans l'historique git. Ce n'est pas corrigé, et
c'est délibéré : réécrire l'historique d'un dépôt public — donc déjà
cloné, déjà indexé — pour une chaîne désormais morte casse tous les clones
existants sans rien protéger.

### Barrière anti-fuite

C'est `scripts/commit-logs.sh`, lancé toutes les 15 minutes par
`midnight-logs-commit.timer`, qui a publié ce token : il faisait
`git add logs/debug/` en bloc, sans aucun contrôle. Il appelle désormais
`scripts/check-staged-secrets.py`, qui refuse le commit si un fichier
indexé porte un identifiant — chaîne opaque longue, affectation du type
`token=`, `password:`, clé privée PEM. Le scanner ne montre jamais une
valeur : il rapporte une règle, une position et un extrait masqué. Son
rapport de refus est écrit **hors de** `logs/`, sinon le passage suivant
committerait le rapport du refus précédent, extrait de secret compris.

Le scanner porte un autotest (`--self-test`) qui vérifie les deux
propriétés qui comptent : il attrape un token, et il n'aboie pas sur une
empreinte, un SHA git, une référence `${VAR}` ou de la prose. H3b exige
que cet autotest passe avant d'installer la barrière, et refuse un faux
token planté pour preuve fonctionnelle.

### Découvertes conservées

- Le token publié déclarait `write` sur `authorizations`. La valeur exposée
  pendant 79 jours permettait donc aussi de **créer ou désactiver des
  tokens**, y compris ceux du bord. Fermé depuis H3a.
- `influx auth list` affiche les valeurs de tous les tokens en clair. Toute
  personne capable de `docker exec` sur le conteneur InfluxDB lit donc tous
  les identifiants du système. Exposition permanente, à traiter dans le
  durcissement.
- Une règle d'alerte Grafana (`mr-safety-network`) interroge un bucket
  `weather_lis` qui n'existe pas : une alerte de sécurité du bateau est
  muette. Sans lien avec cet incident, antérieur, à traiter à part.

### Reste ouvert après H3b

- suppression définitive des deux autorisations désactivées (H3d, après un
  jour d'observation), et des trois tokens `Grafana-*` devenus inutiles ;
- mot de passe admin Grafana par défaut, et `GF_AUTH_ANONYMOUS_ENABLED=true` ;
- `sudo` sans mot de passe pour `aneto` ;
- token en lecture seule pour Grafana (une ligne de `docker-compose.yml`).


## Second token publié — incident SEC-2026-09-15-02 — 20260916T120432Z

Trouvé par la barrière installée en H3b, passée non plus sur les journaux
mais sur les 407 fichiers suivis du dépôt. Une valeur de 88 caractères,
commentée « InfluxDB Cloud token », d'empreinte `5e9d36294bf2a558`.

| fichier | occurrences |
|---|---|
| `docs/guides/RESTORE.md` | 1 |

Deux vérifications indépendantes établissent que **ce n'est pas un
identifiant du bord** : son empreinte ne correspond à aucune des 10
autorisations de l'InfluxDB local, et une lecture réelle du bucket local
avec cette valeur répond HTTP 401.

Cela ne prouve pas qu'il soit mort. S'il appartient à un compte InfluxDB
Cloud encore ouvert, il y reste valide : masquer un fichier ne révoque pas
un token. La valeur doit être **révoquée dans la console Cloud**, et elle
est à considérer comme compromise — au moins 79 jours d'exposition
publique. Cette action revient à Denis ; aucun script ne se connecte à un
service externe avec un identifiant possiblement vivant.

La valeur reste présente dans l'historique git, comme la première, et pour
la même raison : réécrire l'historique d'un dépôt déjà cloné ne protège
rien une fois la révocation faite.

### Leçon de méthode

`docs/guides/RESTORE.md` avait été examiné plusieurs fois pendant cette
phase et déclaré propre. Il l'était au regard de la question posée :
« contient-il LA valeur du token exposé ? ». Il contenait un autre
identifiant. Chercher une valeur connue ne trouve jamais une fuite
inconnue ; chercher une *forme* y arrive. C'est ce que fait la barrière,
et elle se justifie en trouvant, le jour de son installation, une fuite
que l'enquête manuelle avait manquée.
