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

## Pourquoi ne pas l avoir fait maintenant

Parce qu une renumerotation casse toutes les references croisees du type
« voir §5.4 » dans le reste du depot. Il faut les inventorier avant, pas
apres. C est un chantier a part entiere, borne et verifiable, mais ce
n est pas celui de ce commit.
