# Deux gestes reversibles, et un troisieme

**Chantier** : h14b1-v3
**Base** : 3f7b6c28b0fbbb54c8000c0d1cf878d007e5f068
**Commit de contenu** : e33c5deec845cae0106b85ced1b7aed97c63fcc0

Premier chantier de la semaine qui touche la machine. Aucun fichier
supprime, aucune image, aucun conteneur, aucun volume. Trois gestes, tous
defaits par une commande.

## 1. telegraf — FAIT

Le service reclame un parseur `nmea` que le paquet ne fournit pas :

```
E! loading config file /etc/telegraf/telegraf.conf failed:
   error parsing socket_listener, adding parser failed:
   undefined but requested parser: nmea
```

Il n a **jamais demarre une seule fois** depuis son installation. Il etait
la seule unite en echec de la machine. Rien n en depend hors
`multi-user.target`. Sa configuration de 577 ko n est pas touchee.

    pour revenir en arriere :  sudo systemctl unmask telegraf

Unites en echec apres le geste : **0**.

## 2. le compose du workspace OpenClaw — SAUTE (un conteneur du projet workspace tourne)

Hors depot, dans `/home/aneto/.openclaw/workspace`. **Rien n a ete
touche** : la garde a refuse le geste parce qu un conteneur du projet
`workspace` tournait. Aucune sauvegarde n a ete faite, aucun fichier
renomme, aucun `LIRE-MOI` pose.

> **Rectificatif du 2026-09-20, ecrit par H14c.** Le paragraphe qui
> figurait ici etait faux deux fois. Il affirmait au passe des gestes qui
> n ont jamais eu lieu, parce que son texte n etait pas conditionne au
> statut. Et il reposait sur une premisse fausse : ce fichier **ne
> declare aucun Signal K**. Il declare `influxdb`, `grafana`, `regatta`
> et `start-line-worker` — les quatre conteneurs de production du bateau.
> Le defaut 92 est retracte. Le message du commit de journal
> `895ba2c6`, qui annonce un compose retire, est faux lui aussi ; on ne
> reecrit pas l historique, on le corrige ici. Voir
> `logs/debug/premisse-fausse-2026-09-20.md`.

## 3. le conteneur zombie — FAIT

`b03f2697b87c`, `Exited (137)` depuis quatre mois, politique de redemarrage
`unless-stopped`. Sa politique passe a `no`. Il n est **pas** supprime, ni
son image de 1,75 Go : c est H14b-2.

    pour revenir en arriere :  docker update --restart=unless-stopped b03f2697b87c

## Ce que le depot y gagne

Hors du depot, un test ne peut rien. Dans le depot, il peut interdire que
la meme chose y entre un jour. La mesure nouvelle refuse qu un service
nomme `signalk`, ou l image `signalk/signalk-server`, apparaisse dans un
fichier compose du depot — exemples compris. **2 fichiers
compose** sont sous cette mesure.

Elle lit l indentation plutot qu un parseur YAML : PyYAML n est pas
installe sur le Pi, et un test ne doit pas dependre de ce qui manque.

La regle existait depuis le debut du projet, en capitales dans
`ARCHITECTURE-MASTER`. Elle n avait jamais ete mesuree. C est la
quatrieme fois cette semaine qu une regle ecrite se revele non tenue
faute d etre verifiee.

## Tests

| Suite | Resultat |
|---|---|
| `barriere` | ============================== 41 passed in 0.84s ============================== |
| `suite-mcp` | ============================= 109 passed in 40.29s ============================= |
| `suite-mediaman` | ======================= 495 passed, 2 warnings in 22.25s ======================= |

## Ce qui n a pas bouge

`signalk.service` actif et enabled, les quatre conteneurs en marche
intacts, aucune image supprimee, aucun volume touche, aucune ecriture
InfluxDB.

## Reste pour H14b-2

- supprimer le conteneur zombie et l image de 1,75 Go
- `git gc` : 146 Mo d objets en vrac, 344 Mo de `.git`
- defaut 90 : comprendre ce qui declenche mediaman avant de reinstaller
- defaut 91 : quatre unites installees divergent du depot

---
*Ecrit par H14b-1 le 2026-09-20T21:03:15.*
