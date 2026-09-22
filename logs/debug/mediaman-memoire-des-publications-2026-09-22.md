# MediaMan - la memoire des publications

**Date** : 2026-09-22T21:00:29Z
**Base** : `e8f6183d18f2a142e474499101313a0728599d6d`
**Statut** : SUCCESS
**Envoi reel possible a l arrivee** : NON - les trois verrous restent fermes

## Pourquoi ce chantier

MediaMan ne peut aujourd hui rien publier pour de vrai, par construction :
la chaine historique s arrete si `DRY_RUN` ne vaut pas exactement `"true"`,
le pont exige un envoyeur a blanc, et il n accepte qu un resultat portant
`provider_status = DRY_RUN`. C est un verrou volontaire, et il est bien fait.

Avant d ouvrir cette porte - ce sera le chantier suivant - il fallait la
serrure. Elle manquait.

## Ce qui a ete mesure, et qui n etait pas connu

### 1. Le magasin d etat ne memorisait rien entre deux executions

```
# avant
with tempfile.TemporaryDirectory(prefix="mediaman-hist-") as tmpdir:
    db_path = os.path.join(tmpdir, "state.db")
```

Un objet nomme `PublicationStateStore` - memoire des publications - vivait
dans un repertoire detruit a la fin de chaque execution. Sa garantie
"la meme publication n est pas envoyee deux fois" valait a l interieur
d une execution, et pas au dela. A blanc, sans consequence. Le jour ou
`DRY_RUN=false` existera, lancer la commande deux fois aurait publie deux
fois.

Le nom disait *memoire des publications*, la chose etait *memoire des
publications de ce processus*.

### 2. Le journal annoncait une publication qui n avait pas lieu

Mesure faite en lancant deux fois la meme chaine avec une memoire
persistante, en comptant les appels reels a l envoyeur :

```
TOUR 1 : code 0, envois cumules : 1
TOUR 2 : code 0, envois cumules : 1     <- rien n a ete renvoye, c est correct
```

Mais le journal du tour 2 disait :

```
DATA_IN  publication created: id=9669e8fe...
DATA_OUT publication published: state=SENT
```

Rien n avait ete cree, rien n avait ete envoye. Le pont faisait son travail
- `if not created:` retourne l enregistrement `SENT` sans envoyer - et le
journal le racontait de travers. Le jour d une vraie publication, on aurait
lu "published" deux fois pour un seul message parti.

Desormais :

```
DATA_IN  publication already in memory: id=...
DATA_OUT nothing sent, publication already done: state=SENT
SHUTDOWN dry-run publication was already done, nothing re-sent
```

### 3. La suite de tests ecrivait dans le repertoire personnel

La premiere version de ce chantier a cree `~/.mediaman/publications.db` en
lancant simplement les tests : sur le Pi, `pytest` aurait inscrit des
publications de test dans la memoire que la vraie chaine consulte. Corrige,
et verrouille par deux tests : l un relit les fichiers de la suite, l autre
lance la chaine et verifie que la memoire par defaut n apparait pas.

Verification a l execution de ce chantier : `~/.mediaman` etait absente
au demarrage, et l etat apres les tests a ete controle.

### 4. La convention systemd existait deja dans le depot

`event_entrypoint._resolve_state_dir` lit `STATE_DIRECTORY`, pose par systemd
via `StateDirectory=`. Reprise telle quelle plutot que d en inventer une
seconde.

## Ce qui change

- Resolution de la memoire : `MEDIAMAN_STATE_DB` > `STATE_DIRECTORY` >
  `~/.mediaman/publications.db`.
- `MEDIAMAN_STATE_DB=:tmp:` retablit l ancien comportement ephemere.
- Un chemin situe dans le depot est refuse : cet etat est une donnee
  d execution et ne doit jamais atteindre un commit.
- L identite d une publication devient
  `sha256("<mode>:<race_id>:<as_of_utc>:<window_seconds>:<content>")`,
  avec `mode` dans `{dry-run, live}`. Un tir a blanc ne consomme plus le
  creneau d une publication reelle.

## Consequence pratique, a connaitre

**Relancer deux fois le meme tir a blanc ne republiera plus.** C est le but.
Pour repeter un tir sur la meme fenetre et le meme contenu :

```
MEDIAMAN_STATE_DB=:tmp: python3 -m mediaman.historical_entrypoint
```

## Fichiers

| Fichier | Nature | Empreinte d arrivee |
|---|---|---|
| `mediaman/historical_entrypoint.py` | modifie | `5301e8955c7c55de` |
| `tests/mediaman/test_historical_e2e_offline.py` | modifie | `ef985878f174998d` |
| `tests/mediaman/test_historical_entrypoint.py` | modifie | `b932db967c02fc78` |
| `docs/ARCHITECTURE-MASTER.md` | modifie | `f2b23d66f7955034` |
| `tests/mediaman/test_publication_memory.py` | cree | `be1941c3f3395a9d` |

## Tests

| | Avant | Apres |
|---|---|---|
| `tests/mediaman` | 495 | 524 |
| barriere `test_h9b_coherence_doc_code.py` | 48 | 48 |

29 tests ajoutes, aucun test perdu, aucun echec.

## Ce que ce constat ne dit pas

- Il ne dit pas que MediaMan publie. Il ne publie toujours pas, et c est
  voulu a ce stade.
- Il ne dit pas que la chaine evenements a la meme memoire : elle garde son
  propre magasin, dont le repli est `<depot>/var/mediaman-events`, donc a
  l interieur de l arbre de travail. Defaut ouvert ci-dessous.
- Il ne dit rien du lien Signal K vers InfluxDB, ni des quatre enonces faux
  du constat du 22 septembre : ces chantiers restent ouverts.

## Defaut ouvert par ce chantier

**103** - la chaine evenements ecrit son etat d execution dans le depot :
`event_entrypoint._resolve_state_dir` retombe sur `<depot>/var/mediaman-events`
quand ni `MEDIAMAN_STATE_DIR` ni `STATE_DIRECTORY` ne sont poses. Aligner sur
la convention retenue ici.

## Chantier suivant

La jonction : faire de `dry_run` un parametre a trois etages plutot qu une
condition d existence, avec `true` par defaut, un refus si `false` sans
identifiants, et un adaptateur canonique autour de `TelegramSender` - dont
le `send(content)` n accepte pas les parametres exiges par la chaine.
