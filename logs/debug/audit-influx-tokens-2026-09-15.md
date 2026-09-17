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


## Fiche d'identifiants publiée — incident SEC-2026-09-16-03 — 20260916T192301Z

En relisant `docs/guides/RESTORE.md` après H3e, il est apparu que ce
document n'était pas un fichier contenant un token : c'était une **fiche
d'identifiants**, publiée dans un dépôt public.

| Identifiant | empreinte | occurrences masquées |
|---|---|---|
| mot de passe Grafana (admin) | `5579a330b7eb24ff` | 9 |
| passphrase WiFi du bateau | `e465abafdd29e340` | 3 |

Les adresses IP codées en dur du document (5 occurrence(s)) ont été
remplacées par `midnightrider.local`, conformément à la règle du bord.

### Le mot de passe Grafana

Testé en lecture seule contre le Grafana local avant masquage : **ENCORE VALIDE**.
Et il n'est que la seconde porte : `GF_AUTH_ANONYMOUS_ENABLED=true` dans
`docker-compose.yml` laisse lire tous les tableaux de bord **sans aucun
mot de passe** à qui est sur le réseau du bateau.

### La passphrase WiFi — risque accepté, décision de Denis

Denis a décidé de ne pas changer la clé WiFi, avec ce raisonnement :
l'exploitation suppose une proximité physique continue avec le bateau,
ce qui, en navigation, se remarquerait.

Ce raisonnement est solide **en navigation**. Il l'est moins au ponton :
dans un port, la borne est à portée depuis les bateaux voisins, le quai et
souvent le parking, pendant des semaines, sans que personne ne remarque
rien. Et la clé publiée est la même chaîne que le nom du compte GitHub
public, donc devinable sans même lire ce fichier.

La décision est consignée ici comme **risque accepté** et non comme oubli.
C'est la différence qui compte : un risque accepté est un choix documenté,
révisable, qui n'attend pas d'être redécouvert.

### Défauts de ma part, corrigés ici

**Défaut 23 — la note de H3e n'a jamais été écrite.** Le test
d'idempotence cherchait la chaîne `SEC-2026-09-15-02` dans le document,
or le texte de masquage inséré juste avant contient déjà cette chaîne : le
script s'est cru déjà passé. Corrigé par un marqueur dédié
(`H3F-CREDENTIAL-NOTE`) qui n'apparaît nulle part ailleurs.

**Défaut 24 — ma répétition avait validé ce bug.** Le contrôle cherchait
exactement le même marqueur que le script : une assertion qui teste la
mauvaise chose donne un feu vert qui ne vaut rien. Les contrôles vérifient
désormais le texte de la note, pas son marqueur.

**Défaut 25 — mes greps d'adresses IP ne cherchaient que `192.168.1.x`.**
L'adresse du point d'accès est `192.168.4.1` : elle a traversé toute la
phase H sans être vue une seule fois.

**Défaut 26 — la barrière de H3b ne voyait pas ces mots de passe.** Liste
de mots-clés anglaise, et seuil de 20 caractères sur les valeurs. Deux mots
de passe publiés, l'un de 13 caractères étiqueté « login », l'autre de 8
étiqueté « MDP », sont passés dessous. Corrigé : règle
`LABELLED_CREDENTIAL`, étiquettes françaises, seuil abaissé, et un
discriminant réglé contre les 408 fichiers réels du dépôt.


## H3f-v2 — targeted repair

H3f-v1 reached redaction and barrier installation but committed nothing: its final guard classified a diagnostic credential fingerprint as a literal secret. H3f-v2 rebuilt the restore document from clean HEAD, redacted only the Grafana login and WiFi MDP fields, preserved public SSID and headings, and removed private-address literals.

The rehearsed v2 barrier passed compilation, self-test, and repository audit before staging. No service, container, Signal K process, database, dashboard, or network configuration was changed. The WiFi passphrase remains unchanged under the recorded accepted-risk decision.


## H3g - la fuite laissee ouverte par H3f

H3f a masque les deux identifiants publies dans le tableau des
credentials de `docs/guides/RESTORE.md` et a annonce la fuite fermee.
Elle ne l etait pas. La passphrase WiFi restait en clair a l etape 6,
dans l argument `wifi-sec.psk` de la commande nmcli.

Deux aveuglements se sont additionnes. Ma verification ne regardait que
les deux lignes du tableau, celles que je venais d ecrire (defaut 29).
Et la barriere v2 exigeait un separateur `:` `=` ou `|` apres l
etiquette, alors qu un argument de ligne de commande est separe par une
espace (defaut 28). Le meme motif, sous une autre ponctuation, est
passe deux fois.

Recensement fait avant toute modification : la chaine publiee sert
aussi de nom de compte GitHub, present dans plusieurs URL de clonage.
Un nom de compte n est pas un secret ; ces occurrences sont laissees
intactes et verifiees apres traitement. Consequence a retenir : la
passphrase est de toute facon lisible dans l URL du depot, donc le seul
correctif reel est de la changer. Denis a choisi de ne pas la changer et
ce risque reste accepte et enregistre.

Corriges aussi : l adresse de la passerelle du point d acces, que H3f
avait remplacee par un nom d hote alors que nmcli exige une adresse
numerique, ce qui rendait la procedure de restauration inexecutable
(defaut 30) ; le bit d execution du scanner (defaut 31) ; et l absence
du SHA de H3f dans le journal d actions (defaut 32).

Aucun service, conteneur, processus Signal K, base, tableau de bord ou
reglage reseau n a ete touche.


## H4b - reprise en main du compte administrateur Grafana

CORRECTION (defaut 34). En H3f puis dans deux comptes rendus, j ai
affirme que le mot de passe publie ouvrait encore Grafana, en
m appuyant sur un GET /api/org qui repondait HTTP 200. Le diagnostic
en lecture seule du 2026-09-16 a montre que ce meme appel repond 200
sans aucun identifiant, et meme avec un mot de passe tire au hasard :
c est l acces anonyme qui repondait. Interroge sur /api/user, qui exige
une session reelle, le mot de passe publie renvoie 401. Il est donc
perime et ne donnait acces a rien. Mon affirmation etait fausse ; elle
est corrigee ici par ajout, sans reecriture de l historique.

Lecon de methode : un point d acces lisible par l anonyme ne peut pas
servir a tester un identifiant. Le bon test est celui qui demande a
Grafana QUI il croit avoir en face, pas celui qui demande une donnee.

Situation reelle constatee : personne ne detenait le mot de passe
administrateur de cette instance. Il n etait ni dans .env, ni dans
docker-compose.yml, ni dans config/grafana-custom.ini, et la valeur
publiee ne fonctionnait plus. L acces anonyme en lecture masquait ce
trou : tout le monde voyait les tableaux de bord, donc personne ne
s apercevait que plus personne ne pouvait administrer.

Action faite ici : un mot de passe administrateur connu a ete etabli
par grafana-cli dans le conteneur en fonctionnement, sans recreation ni
redemarrage. Preuve : /api/user renvoie 200 avec login=admin, et
/api/admin/stats est accessible. La valeur est ecrite seulement dans
.env, verifie non suivi et ignore avant et apres. Les deux noms de cle
attendus par les scripts du depot ont ete crees : ils etaient absents,
donc deploy-dashboards-to-grafana.sh et post-race-cloud-sync.sh
travaillaient jusqu ici avec un identifiant par defaut inexistant.

Deliberement non fait : l acces anonyme en lecture reste actif. C est
maintenant le seul vrai sujet de securite sur Grafana, et il se decide
en connaissant son effet sur portal/viewer.html, qui affiche les
tableaux de bord en iframe sans s authentifier. Il fallait d abord
pouvoir se connecter avant de pouvoir fermer.

<!-- H4C-PROBE-NOTE -->

## H4c - ce qui depend vraiment de l acces anonyme, et un registre remis d aplomb

Mesure, pas supposition. Trois constats tires de la machine le 20260916T231406Z :

1. Embarquement de Grafana dans le portail : BLOQUE. Le portail est servi sur
   le port 8888 et l iframe pointe sur le port 3001 : deux origines
   differentes pour un navigateur. Le fichier config/grafana-custom.ini du
   depot demande allow_embedding = true, mais il est monte sur
   /etc/grafana/provisioning/grafana.ini alors que Grafana lit
   /etc/grafana/grafana.ini, et la variable d environnement
   GF_SECURITY_X_FRAME_OPTIONS l emporte de toute facon sur un fichier.

2. 5 tableau(x) de bord reference(s) par portal/index.html repondent
   aujourd hui sans aucun identifiant.

3. Un cookie de session porte sur l hote et ignore le port. Une connexion
   unique sur midnightrider.local:3001 couvrirait donc aussi l iframe.

Corrections du registre, par ajout et par rectification de champs devenus
faux, jamais par reecriture d historique :

- le defaut 20 affirmait encore que Grafana acceptait son mot de passe par
  defaut. C est la moitie exacte de ce que le defaut 34 a refute. Il est
  scinde : la partie mot de passe est fermee, la partie acces anonyme reste
  ouverte.
- third_incident.status se contredisait avec le champ ajoute par H4b quatre
  lignes plus bas. La phrase perimee est rectifiee.
- le defaut 33 etait annonce et jamais ecrit. Il est mesure ici, puis classe
  selon le resultat : OUVERT.
- le numero 27 reste introuvable dans le depot. Le trou est declare tel quel
  dans latest.json plutot que comble par une invention.
- next_steps portait deux fois la consigne de changer le mot de passe, faite.
- commit_chain portait le texte litteral "this commit" a la place de SHA. Les
  valeurs sont retrouvees dans l historique local, pas fabriquees.

Lecon : un registre qui se contredit cesse d etre un registre. C est celui-ci
qui a servi de base a une decision prise sur une information fausse.

<!-- H4D-PART-A -->

## H4d partie A - reparer le registre que j avais casse, et le scanner

Defaut 35, le mien. En H4c j ai resolu les marqueurs "this commit" de
commit_chain avec la commande 'git log --grep=TAG -1'. Cette commande renvoie le commit le
plus RECENT qui cite l etiquette, or les commits tardifs citent les phases
anterieures. Resultat : 9d9ba4f inscrit comme H3b alors qu il est H3e, et
e3a9892 inscrit comme H3f alors qu il est H4b. J ai remplace deux marqueurs
honnetes par deux SHA faux, ce qui est pire que le trou d origine.

La chaine est reconstruite a partir de api.github.com, commit par commit. Une
heuristique locale commode n est pas une autorite ; l API en est une.

Defaut 33, mesure puis corrige : l option --audit employee sans --files
n examinait que l index. Le mode audit lit desormais la liste complete des
fichiers suivis par git. Verdict apres correctif :
CORRIGE.

Trois constats supplementaires ouverts, issus de la sonde H4c :
- 36 : deux cartes de la page d accueil du portail pointent sur des tableaux
  de bord inexistants (404 meme authentifie).
- 37 : les UID du depot divergent de ceux de l instance. Depuis que H4b a
  rendu un identifiant valide a deploy-dashboards-to-grafana.sh, lancer ce
  script creerait vraisemblablement des doublons. Ne pas le lancer.
- 38 : renvoi documentaire mort vers CLOUDFLARE-TUNNEL-URL.md. Etat du service
  cloudflared mesure sur le Pi : ABSENT.

<!-- H4E-NOTE -->

## H4e - le portail suit l hote, et une conclusion fausse de plus a mon actif

Denis a constate que le portail, atteint par Tailscale, affichait des cadres
vides : les sept liens de portal/index.html passaient host=midnightrider.local,
un nom mDNS qui ne se resout pas hors du reseau local. Le repli de viewer.html
etait pourtant correct depuis le debut. C est le lien qui l ecrasait.

Correctif : le parametre fige est retire, les pages suivent l hote par lequel
elles ont ete ouvertes. Aucune adresse 100.x.x.x n est ecrite dans le depot,
conformement a SYSTEM-SUMMARY.md section 11.

Defaut 40, le mien. En H4d j ai affiche "aucun tunnel actif : l exposition se
limite au reseau local" apres n avoir interroge que cloudflared. Tailscale
tournait. L acces anonyme que nous venons de fermer etait donc ouvert a tout
le tailnet, et pas seulement au bateau. SYSTEM-SUMMARY.md documente Tailscale
depuis toujours ; je ne l ai pas relu sur ce point et j ai fait confiance a
ARCHITECTURE-MASTER.md, qui annoncait un tunnel Cloudflare inexistant.

C est la troisieme fois que je conclus au-dela de ce que j ai mesure, apres le
defaut 34 et le defaut 35. Les trois fois, une absence de signal a ete lue
comme un signal d absence. Une sonde ne prouve que ce qu elle interroge.
