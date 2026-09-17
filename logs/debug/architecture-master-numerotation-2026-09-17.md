# ARCHITECTURE-MASTER.md — numérotation à arbitrer

**Date du constat :** 2026-09-17
**Statut :** ouvert, non corrigé — demande un arbitrage éditorial

Le dédoublonnage de la section 8 (4 copies excedentaires retirees) a ete
fait dans le meme commit que ce constat, parce qu il etait purement
mecanique : les 5 blocs etaient identiques a l octet.

Ce qui suit ne l est pas. Corriger la numerotation demande de decider ce
que le plan du document DOIT etre. Ce n est pas une reparation, c est une
decision. Elle est donc laissee a Denis.

## Ce qui a ete mesure, hors blocs de code

| Probleme | Emplacements |
|----------|--------------|
| §5.6 utilise deux fois | `5.6 Pression atmospherique` et `5.6 AIS Competitor Tracker` |
| §5.8 utilise deux fois | `5.8 Configuration Backup` et `5.8 Plugin Deployment Pattern` |
| §7 utilise deux fois | `7. UNITES SI` et `7. STRUCTURE DES LOGS` |
| Ordre : §9 avant §8 | `## 9. REGLES ABSOLUES` precede `## 8. SIGNAL K` |
| Sous-sections orphelines | `## 10. SECURITE` est suivi de `## 9.1` a `## 9.4` |
| Sections rejetees en fin | `5.8`, `5.9`, `5.10` et `7. STRUCTURE DES LOGS` apparaissent APRES `## 13` |

Les 62 clotures de blocs de code sont equilibrees : il n y a pas de bloc
non ferme. Un premier balayage avait suggere des titres de niveau 1
anormaux ; il ne tenait pas compte des blocs de code et ce constat est
retire.

## Plan cible propose, a valider

1. Renumeroter en deux temps seulement, jamais en une passe automatique.
2. Rattacher `9.1` a `9.4` (secrets, .gitignore, pare-feu, mode silencieux)
   a la section SECURITE, sous la forme `10.1` a `10.4`.
3. Deplacer `## 8. SIGNAL K` avant `## 9. REGLES ABSOLUES` pour rendre
   l ordre croissant.
4. Renommer le second `§7` en `§14. STRUCTURE DES LOGS` et le deplacer
   avec les autres sections de fin.
5. Renommer le second `§5.8` en `§5.11 Plugin Deployment Pattern` et le
   second `§5.6` en `§5.7 AIS Competitor Tracker`.
6. Verifier apres coup qu aucun numero n est utilise deux fois et que
   l ordre des titres de niveau 2 est croissant.

## Constat annexe : liens relatifs casses dans docs/INDEX.md

Mesure du 2026-09-17 : dans `docs/INDEX.md`, 20 liens relatifs ne
resolvent pas, pour 16 cibles distinctes. La cause est systematique et
anterieure a ce commit : le fichier est DANS `docs/` mais ecrit ses
cibles comme s il etait a la racine. Exemples mesures :

| Lien ecrit | Resout en | Etat |
|------------|-----------|------|
| `docs/ARCHITECTURE-MASTER.md` | `docs/docs/ARCHITECTURE-MASTER.md` | absent |
| `SOFTWARE/SIGNAL-K-CONFIGURATION.md` | `docs/SOFTWARE/...` | dossier absent |
| `OPERATIONS/TROUBLESHOOTING.md` | `docs/OPERATIONS/...` | dossier absent |
| `../CONTRIBUTING.md` | `CONTRIBUTING.md` | absent du depot |

Ce n est pas corrige ici. Pour chaque cible il faut d abord decider si le
document manque ou si le lien est mal ecrit : ce sont deux reparations
differentes. Chantier distinct, a borner separement.

## Defaut 61 — un job automatique publie du travail abandonne

Constat du 2026-09-17, decouvert en tentant ce commit.

`h7d-v2` s est arretee a son etape 8 sur son propre garde-fou, sans
commiter : `README.md` etait hors liste blanche. Correct. Mais l etape 4
avait utilise `git mv`, qui **indexe** le renommage. Huit minutes plus
tard, le job d auto-commit des journaux, qui tourne toutes les 15 minutes,
a commite et pousse cet index : commit `80f3980`.

Ce qui a ete publie sans que personne ne le decide :

| Publie | Consequence |
|--------|-------------|
| le renommage `docs/SYSTEM-SUMMARY.md` → `docs/SYSTEM-OVERVIEW-1PAGE.md` | 4 references cassees sur `main` |
| `logs/latest.json` | declare `h7d-v2` **SUCCESS** et liste 5 documents modifies qui ne sont pas dans le commit |
| `logs/oc-actions.log` | 5 lignes decrivant des modifications non publiees |
| `logs/debug/architecture-master-numerotation-2026-09-17.md` | fichier non suivi, ramasse par `git add logs/` |

Le meme mecanisme est deja identifie comme la cause de
`SEC-2026-09-14-01` : c est lui qui avait publie l autorisation InfluxDB
dans ce depot public.

Deux consequences de conception, appliquees des ce commit :

1. un script ne doit **rien indexer** avant son etape de commit, et ne
   doit ecrire dans `logs/` qu a cet instant ;
2. un script doit armer un piege de sortie qui, en cas d arret anormal,
   vide l index et remet `logs/` a HEAD.

Ce qui reste a decider, et n est pas fait ici : le job lui-meme devrait
refuser de commiter quand l index contient autre chose que `logs/`.
C est une modification de service, hors perimetre d un commit de
documentation.

## Pourquoi ne pas l avoir fait maintenant

Parce qu une renumerotation casse toutes les references croisees du type
« voir §5.4 » dans le reste du depot. Il faut les inventorier avant, pas
apres. C est un chantier a part entiere, borne et verifiable, mais ce
n est pas celui de ce commit.
