"""H9b - la documentation canonique doit pointer vers ce qui existe.

Le defaut 65 a survecu des mois parce que docs/ARCHITECTURE-MASTER.md
declarait trois outils MCP inexistants sous un en-tete "Source-Verified"
avec une coche verte chacun. Personne ne verifie ce qu'un document
canonique certifie deja. Ces tests retirent cette possibilite : un chemin
cite entre accents inverses doit exister, et les outils annonces doivent
etre ceux que le serveur declare vraiment.
"""

import os
import re
import subprocess

import pytest

RACINE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
ARCH = os.path.join(RACINE, "docs", "ARCHITECTURE-MASTER.md")
RACING = os.path.join(RACINE, "mcp", "servers", "racing.js")
CLIENT = os.path.join(RACINE, "mediaman", "mcp_client.py")

EXTENSIONS = (
    ".md", ".py", ".js", ".json", ".sh", ".yml", ".yaml",
    ".ini", ".service", ".timer", ".txt", ".conf",
)

# Exceptions nommees, avec leur raison. Toute entree ajoutee ici doit dire
# pourquoi, sinon la barriere se vide d'elle-meme.
EXCEPTIONS = {
    "./docker-compose.yaml":
        "ordre de recherche de docker compose, pas un fichier du depot",
}

NOMS_MORTS = ("racing.get_position", "racing.get_sog", "racing.get_cog")


def _lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return f.read()


def _ignore_par_git(chemin_relatif):
    """Un fichier volontairement non versionne n'a pas a exister ici."""
    try:
        r = subprocess.run(
            ["git", "check-ignore", "-q", chemin_relatif],
            cwd=RACINE, timeout=10,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def chemins_cites(texte):
    """Chemins relatifs au depot cites entre accents inverses."""
    vus = []
    for m in re.finditer(r"`([^`\n]+)`", texte):
        s = m.group(1).strip()
        if " " in s or "/" not in s:
            continue
        if not s.endswith(EXTENSIONS):
            continue
        if s.startswith(("http", "~", "/dev/", "/etc/", "/var/",
                         "/home/", "/tmp/", "/usr/", "/opt/", "/proc/")):
            continue
        vus.append(s)
    return sorted(set(vus))


class TestCheminsCites:
    """Un chemin ecrit entre accents inverses est une promesse verifiable."""

    def test_tout_chemin_cite_dans_architecture_master_existe(self):
        manquants = []
        for c in chemins_cites(_lire(ARCH)):
            if c in EXCEPTIONS:
                continue
            relatif = c[2:] if c.startswith("./") else c
            if os.path.exists(os.path.join(RACINE, relatif)):
                continue
            if _ignore_par_git(relatif):
                continue
            manquants.append(c)
        assert manquants == [], (
            "docs/ARCHITECTURE-MASTER.md cite des fichiers qui n'existent "
            "pas : %s" % manquants
        )

    def test_chaque_exception_porte_une_raison(self):
        for chemin, raison in EXCEPTIONS.items():
            assert raison and len(raison) > 15, (
                "l'exception %s n'explique pas pourquoi elle existe" % chemin
            )


# Buckets reellement presents sur le serveur, releve du 2026-09-18 par
# GET /api/v2/buckets : il n y en a qu un. Toute autre valeur citee dans
# la documentation est une commande que personne ne pourra executer.
BUCKETS_ATTESTES = {
    "midnight_rider":
        "seul bucket present sur localhost:8086, releve le 2026-09-18",
    "signalk-cloud":
        "cible de replication InfluxDB Cloud, decrite dans docs/setup/INFLUXDB-CONFIG.md",
}

BUCKETS_FICTIFS_ADMIS = {
    "nonexistent": "fixture de test negatif, docs/INFLUXDB-AUTH-INTEGRATION.md",
}

# L organisation du serveur local, et l identifiant de l organisation
# InfluxDB Cloud qui apparait tel quel dans les commandes de replication.
ORGS_ATTESTEES = {
    "MidnightRider":
        "unique organisation du serveur local, relevee le 2026-09-18",
    "48a34d6463cef7c9":
        "identifiant de l organisation InfluxDB Cloud, docs/setup/INFLUXDB-CONFIG.md",
}

# H11 a ecrit ces motifs trop etroits puis s est declare victorieux :
# INFLUX(?:DB)?_ ne voyait pas INFLUX_DB_BUCKET, et l organisation n etait
# cherchee que sous forme de variable, jamais sous le mot-cle nu org=.
# Un bucket faux et six organisations fausses sont passes au travers.
MOTIFS_BUCKET = (
    re.compile(r"""from\(\s*bucket\s*:\s*["'`]([A-Za-z0-9_-]+)"""),
    re.compile(r"""\bbucket\s*[:=]\s*["'`]([A-Za-z0-9_-]+)["'`]"""),
    re.compile(r"""\bINFLUX[A-Z_]*BUCKET\s*[:=]\s*["'`]?([A-Za-z0-9_${}-]+)"""),
    re.compile(r"""--bucket[= ]+["'`]?([A-Za-z0-9_${}-]+)"""),
)

MOTIFS_ORG = (
    re.compile(r"""\bINFLUX[A-Z_]*ORG\s*[:=]\s*["'`]?([A-Za-z0-9_${}-]+)"""),
    re.compile(r"""\borg\s*[:=]\s*["'`]([A-Za-z0-9_${}-]+)["'`]"""),
    re.compile(r"""--org[= ]+["'`]?([A-Za-z0-9_${}-]+)"""),
)


def _est_une_variable(valeur):
    """$INFLUX_CLOUD_BUCKET nomme une variable, pas un bucket."""
    return valeur.startswith("$") or "{" in valeur


def fichiers_documentation():
    trouves = []
    for base, dossiers, fichiers in os.walk(RACINE):
        dossiers[:] = [d for d in dossiers
                       if d not in (".git", "node_modules", "logs", "__pycache__")]
        for f in fichiers:
            if not f.endswith(".md"):
                continue
            chemin = os.path.join(base, f)
            relatif = os.path.relpath(chemin, RACINE)
            if relatif.startswith("docs" + os.sep) or os.sep not in relatif:
                trouves.append(chemin)
    return sorted(trouves)


class TestNomsDeBucket:
    """Un bucket cite dans la documentation doit exister sur le serveur.

    Le defaut 74 : deux guides proposaient une commande de copier-coller
    sur un bucket `signalk` que le serveur n a pas. L un des deux etait le
    guide de recuperation - celui qu on lit quand ca va deja mal.
    """

    def test_tout_bucket_cite_est_atteste(self):
        connus = set(BUCKETS_ATTESTES) | set(BUCKETS_FICTIFS_ADMIS)
        fautes = []
        for chemin in fichiers_documentation():
            with open(chemin, encoding="utf-8") as f:
                for numero, ligne in enumerate(f, 1):
                    if ligne.lstrip().startswith(">"):
                        continue  # bloc de correction : on y cite le passe
                    for motif in MOTIFS_BUCKET:
                        for nom in motif.findall(ligne):
                            if _est_une_variable(nom):
                                continue
                            if nom not in connus:
                                fautes.append("%s:%d -> %s" % (
                                    os.path.relpath(chemin, RACINE), numero, nom))
        assert fautes == [], (
            "buckets cites qui n existent pas sur le serveur : %s" % fautes)

    def test_toute_organisation_citee_est_attestee(self):
        """Le serveur local n a qu une organisation : MidnightRider."""
        fautes = []
        for chemin in fichiers_documentation():
            with open(chemin, encoding="utf-8") as f:
                for numero, ligne in enumerate(f, 1):
                    if ligne.lstrip().startswith(">"):
                        continue
                    for motif in MOTIFS_ORG:
                        for nom in motif.findall(ligne):
                            if _est_une_variable(nom):
                                continue
                            if nom not in ORGS_ATTESTEES:
                                fautes.append("%s:%d -> %s" % (
                                    os.path.relpath(chemin, RACINE), numero, nom))
        assert fautes == [], (
            "organisations citees qui ne sont pas attestees : %s" % fautes)

    def test_chaque_valeur_declaree_porte_sa_raison(self):
        tables = (BUCKETS_ATTESTES, BUCKETS_FICTIFS_ADMIS, ORGS_ATTESTEES)
        for table in tables:
            for nom, raison in table.items():
                assert raison and len(raison) > 15, (
                    "la valeur %s est declaree sans raison" % nom)


class TestLaBarriereVoitCeQuElleDoitVoir:
    """Ces tests interrogent le detecteur, pas le corpus.

    Defaut 75 et 76 : H11 a affiche BUCKETS_FANTOMES_RESTANTS=0 et
    considere le defaut 74 ferme, alors qu il restait INFLUX_DB_BUCKET=signalk
    dans docs/setup/INFLUXDB-CONFIG.md et six org="midnight-rider" dans
    docs/INFLUXDB-AUTH-INTEGRATION.md. Le corpus n etait pas propre : le
    detecteur etait aveugle. Un corpus qui passe ne prouve rien tant que
    personne n a verifie que la barriere sait voir.

    Chaque echantillon ci-dessous est une ligne reellement presente dans le
    depot, ou qui y a ete presente. Ajouter une forme ici avant de la
    corriger est la bonne facon d etendre cette barriere.
    """

    ECHANTILLONS_BUCKET = (
        ("    - INFLUX_DB_BUCKET=signalk", "signalk"),
        ("    - INFLUX_BUCKET=midnight_rider", "midnight_rider"),
        ("INFLUXDB_BUCKET=midnight_rider", "midnight_rider"),
        ('export INFLUX_CLOUD_BUCKET="signalk-cloud"', "signalk-cloud"),
        ('    --bucket "signalk-cloud" \\', "signalk-cloud"),
        ('from(bucket:"midnight_rider")', "midnight_rider"),
        ('  bucket: "midnight_rider"', "midnight_rider"),
    )

    ECHANTILLONS_ORG = (
        ('    org="midnight-rider",', "midnight-rider"),
        ("INFLUX_ORG=MidnightRider", "MidnightRider"),
        ("    - INFLUX_DB_ORG=MidnightRider", "MidnightRider"),
        ("  --org MidnightRider \\", "MidnightRider"),
        ('export INFLUX_CLOUD_ORG="48a34d6463cef7c9"', "48a34d6463cef7c9"),
    )

    def test_les_motifs_de_bucket_voient_les_formes_du_depot(self):
        for ligne, attendu in self.ECHANTILLONS_BUCKET:
            vus = set()
            for motif in MOTIFS_BUCKET:
                vus.update(motif.findall(ligne))
            assert attendu in vus, (
                "aucun motif de bucket ne voit %r ; attendu %s, vu %s"
                % (ligne, attendu, sorted(vus)))

    def test_les_motifs_d_organisation_voient_les_formes_du_depot(self):
        for ligne, attendu in self.ECHANTILLONS_ORG:
            vus = set()
            for motif in MOTIFS_ORG:
                vus.update(motif.findall(ligne))
            assert attendu in vus, (
                "aucun motif d organisation ne voit %r ; attendu %s, vu %s"
                % (ligne, attendu, sorted(vus)))

    def test_les_variables_ne_sont_pas_prises_pour_des_valeurs(self):
        assert _est_une_variable("$INFLUX_CLOUD_BUCKET")
        assert _est_une_variable("${INFLUX_ORG}")
        assert not _est_une_variable("midnight_rider")
        assert not _est_une_variable("MidnightRider")


class TestOutilsDeclares:
    """Les outils annonces doivent etre ceux que le serveur declare."""

    def _outils_du_serveur(self):
        texte = _lire(RACING)
        debut = texte.index("const TOOLS") if "const TOOLS" in texte else 0
        return set(re.findall(r"name:\s*'(get_[a-z_]+)'", texte[debut:]))

    def _outils_de_la_liste_blanche(self):
        texte = _lire(CLIENT)
        bloc = texte[texte.index("TOOL_WIRE_MAPPING"):texte.index("STARTUP_TIMEOUT_SECONDS")]
        return set(re.findall(r"'wire_name':\s*'([a-z_]+)'", bloc))

    def test_serveur_et_liste_blanche_declarent_les_memes_outils(self):
        serveur = self._outils_du_serveur()
        blanche = self._outils_de_la_liste_blanche()
        assert serveur == blanche, (
            "le serveur declare %s, la liste blanche autorise %s"
            % (sorted(serveur), sorted(blanche))
        )

    def test_le_serveur_declare_exactement_deux_portes(self):
        assert self._outils_du_serveur() == {
            "get_historical_snapshot", "get_snapshot"
        }

    def test_aucun_outil_mort_presente_comme_disponible(self):
        """Les noms morts ne peuvent subsister que dans le recit du defaut."""
        texte = _lire(ARCH)
        for ligne in texte.splitlines():
            if not any(n in ligne for n in NOMS_MORTS):
                continue
            assert ligne.lstrip().startswith(">"), (
                "un outil supprime est cite hors du bloc de correction : %s"
                % ligne.strip()[:100]
            )

    def test_la_doc_cite_les_deux_portes_reelles(self):
        texte = _lire(ARCH)
        for nom in ("racing.get_historical_snapshot", "racing.get_snapshot"):
            assert nom in texte, "%s absent de l'architecture maitresse" % nom



# ---------------------------------------------------------------------------
# H12 - un document de procedure doit pouvoir etre suivi
#
# La version 1.1 de docs/ops/RECOVERY-GUIDE-SAFE.md citait 53 chemins dont 2
# existaient, et son STEP 1 prescrivait de demarrer Signal K avec
# docker-compose - l action que l architecture interdit en capitales. Un
# document de secours faux est pire qu absent : on le suit quand on n a plus
# le temps de verifier.
#
# La liste sous garde est courte a dessein. Le recensement du 2026-09-18 a
# trouve 189 chemins morts dans la documentation canonique, dont 119 dans le
# seul docs/INDEX.md. Tout mettre sous garde d un coup obligerait a tout
# corriger dans le meme passage. Les documents entrent ici a mesure qu ils
# sont assainis.
# ---------------------------------------------------------------------------

DOCUMENTS_SOUS_GARDE = (
    "docs/ops/RECOVERY-GUIDE-SAFE.md",
    "docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md",
)

EXTENSIONS_DE_FICHIER = (
    "js", "py", "sh", "md", "json", "yml", "yaml", "conf", "service", "timer",
)

MOTIF_CHEMIN = re.compile(
    r"[A-Za-z0-9_${}./~-]*[A-Za-z0-9_-]+\.(?:%s)\b" % "|".join(EXTENSIONS_DE_FICHIER)
)

# Ce qui ressemble a un chemin sans en etre un.
NON_CHEMINS = {
    "navigation.position",   # nom de measurement InfluxDB
    "telegraf.service",      # unite systeme absente du depot - defaut 71
    "Node.js",
}

VERBE_DOCKER = re.compile(
    r"\bdocker[- ](?:compose\s+)?(?:up|run|start|ps|create|restart)\b"
)


def _index_des_noms():
    """Tous les noms de fichiers du depot, pour resoudre un nom nu."""
    noms = set()
    for base, dossiers, fichiers in os.walk(RACINE):
        dossiers[:] = [d for d in dossiers
                       if d not in (".git", "node_modules", "__pycache__")]
        noms.update(fichiers)
    return noms


def chemins_morts(document, noms=None):
    """Chemins cites par un document et introuvables dans le depot.

    Lit TOUTES les lignes, pas seulement les accents inverses : les chemins
    faux de la version 1.1 vivaient dans des blocs de code et des
    arborescences ASCII, invisibles d un balayage des accents inverses.
    """
    if noms is None:
        noms = _index_des_noms()
    morts = []
    with open(os.path.join(RACINE, document), encoding="utf-8") as f:
        for numero, ligne in enumerate(f, 1):
            if ligne.lstrip().startswith(">"):
                continue  # bloc de rectification : on y cite ce qui n existe plus
            for brut in MOTIF_CHEMIN.findall(ligne):
                if brut in NON_CHEMINS:
                    continue
                c = brut.replace("${PROJECT_ROOT}/", "").replace("$PROJECT_ROOT/", "")
                if c.startswith(("~", "/", "$")):
                    continue  # hors depot, non verifiable ici
                c = c.lstrip("./")
                if os.path.exists(os.path.join(RACINE, c)):
                    continue
                if "/" not in c and c in noms:
                    continue  # nom nu, resolu ailleurs dans le depot
                morts.append((numero, brut))
    return morts


def lignes_de_commande(document):
    """Les lignes situees a l interieur des blocs de code d un document."""
    dedans = False
    with open(os.path.join(RACINE, document), encoding="utf-8") as f:
        for numero, ligne in enumerate(f, 1):
            if ligne.lstrip().startswith("```"):
                dedans = not dedans
                continue
            if dedans:
                yield numero, ligne.rstrip("\n")


def commandes_docker_sur_signalk(document):
    """Commandes qui feraient tourner Signal K sous Docker, ou l y chercheraient."""
    fautes = []
    for numero, ligne in lignes_de_commande(document):
        if VERBE_DOCKER.search(ligne) and re.search(r"\bsignalk\b", ligne):
            fautes.append((numero, ligne.strip()))
        elif re.search(r"docker/signalk", ligne):
            fautes.append((numero, ligne.strip()))
    return fautes


class TestUnDocumentDeProcedurePeutEtreSuivi:
    """Ce qu un document de secours promet doit exister."""

    def test_les_documents_sous_garde_ne_citent_aucun_chemin_mort(self):
        noms = _index_des_noms()
        fautes = []
        for document in DOCUMENTS_SOUS_GARDE:
            for numero, brut in chemins_morts(document, noms):
                fautes.append("%s:%d -> %s" % (document, numero, brut))
        assert fautes == [], (
            "%d chemin(s) cite(s) et introuvable(s) : %s"
            % (len(fautes), fautes[:12])
        )

    def test_aucune_commande_ne_cherche_signal_k_dans_docker(self):
        """Signal K tourne sous systemctl. Jamais sous Docker.

        Le conteneur orphelin `signalk`, Exited (137) depuis quatre mois, est
        selon toute vraisemblance ne du STEP 1 de la version 1.1, qui donnait
        le docker-compose up pour le creer.
        """
        fautes = []
        for document in DOCUMENTS_SOUS_GARDE:
            for numero, ligne in commandes_docker_sur_signalk(document):
                fautes.append("%s:%d -> %s" % (document, numero, ligne[:70]))
        assert fautes == [], (
            "commande(s) qui traitent Signal K comme un conteneur : %s" % fautes
        )

    def test_le_guide_de_secours_prescrit_systemctl(self):
        chemin = os.path.join(RACINE, "docs", "ops", "RECOVERY-GUIDE-SAFE.md")
        with open(chemin, encoding="utf-8") as f:
            texte = f.read()
        assert "systemctl start signalk" in texte, (
            "le guide de secours ne dit pas comment demarrer Signal K"
        )


class TestLeDetecteurDeCheminsVoitCeQuIlDoitVoir:
    """Le detecteur est teste sur les formes qui l ont pris en defaut.

    Un premier detecteur ne lisait que les accents inverses. Passe sur la
    version 1.1 du guide, il trouvait zero chemin mort - alors qu il y en
    avait 62. Ses angles morts etaient les blocs de code et les
    arborescences ASCII, c est-a-dire l endroit ou vivent les commandes.
    """

    ECHANTILLONS = (
        "${PROJECT_ROOT}/docker/signalk/mcp/racing-server.js",
        "bash ${PROJECT_ROOT}/docker/signalk/mcp/test-servers.sh",
        "  |-- astronomical-server.js      (4 tools)",
        "*/5 * * * * ${PROJECT_ROOT}/docker/signalk/scripts/buoy-logger.sh",
        '    "command": "${PROJECT_ROOT}/docker/signalk/mcp/polar-server.js",',
    )

    def test_le_motif_voit_les_chemins_hors_accents_inverses(self):
        for ligne in self.ECHANTILLONS:
            assert MOTIF_CHEMIN.findall(ligne), (
                "le motif de chemin ne voit rien dans %r" % ligne
            )

    ECHANTILLONS_DOCKER = (
        'docker ps | grep -E "influxdb|signalk|grafana"',
        "cd ${PROJECT_ROOT}/docker/signalk",
        "docker-compose up -d   # signalk",
    )

    def test_le_controle_docker_voit_les_formes_de_la_version_1_1(self):
        for ligne in self.ECHANTILLONS_DOCKER:
            vu = (VERBE_DOCKER.search(ligne) and re.search(r"\bsignalk\b", ligne)) \
                 or re.search(r"docker/signalk", ligne)
            assert vu, "le controle ne voit pas %r" % ligne


# ---------------------------------------------------------------------------
# H12b - un compte annonce est une promesse verifiable
#
# H12 a ecrit "expect 80 passed" dans le guide de secours et a ajoute cinq
# tests dans le meme commit. Le guide etait faux a la seconde ou il etait
# pousse. Rien ne l a vu : la barriere verifiait les chemins, pas les nombres.
#
# Seul tests/mcp passe sous garde. Le comptage statique des "def test_" y
# donne exactement ce que pytest compte. Il n en va pas de meme pour
# tests/mediaman, ou pytest compte 495 la ou les "def test_" sont 492 : y
# poser la meme barriere reviendrait a mesurer autre chose que ce qu elle
# pretendrait mesurer. C est l erreur que ce depot repete depuis deux jours ;
# on ne la reproduit pas pour faire un chiffre de plus.
# ---------------------------------------------------------------------------

GUIDE_DE_SECOURS = os.path.join("docs", "ops", "RECOVERY-GUIDE-SAFE.md")


def _compter_tests(dossier):
    """Nombre de fonctions de test declarees sous un dossier."""
    total = 0
    for base, dossiers, fichiers in os.walk(os.path.join(RACINE, dossier)):
        dossiers[:] = [d for d in dossiers if d != "__pycache__"]
        for nom in fichiers:
            if nom.startswith("test_") and nom.endswith(".py"):
                with open(os.path.join(base, nom), encoding="utf-8") as f:
                    total += sum(1 for l in f if l.lstrip().startswith("def test_"))
    return total


class TestUnCompteAnnonceEstVerifiable:
    """Ce qu un document promet en chiffres doit se mesurer."""

    def test_le_guide_annonce_le_bon_nombre_de_tests_mcp(self):
        reel = _compter_tests("tests/mcp")
        with open(os.path.join(RACINE, GUIDE_DE_SECOURS), encoding="utf-8") as f:
            texte = f.read()
        annonces = set(int(x) for x in re.findall(
            r"pytest tests/mcp[^\n\d]{0,24}?(\d+) passed", texte))
        assert annonces, "le guide n annonce plus aucun compte pour tests/mcp"
        assert annonces == {reel}, (
            "le guide annonce %s pour tests/mcp, le depot en declare %d"
            % (sorted(annonces), reel))

    def test_npm_test_lance_une_suite_qui_existe(self):
        """mcp/package.json a designe pendant des mois un fichier absent."""
        import json as _json
        with open(os.path.join(RACINE, "mcp", "package.json"), encoding="utf-8") as f:
            paquet = _json.load(f)
        commande = paquet.get("scripts", {}).get("test", "")
        assert commande, "mcp/package.json ne declare aucune commande de test"
        cibles = re.findall(r"tests/[A-Za-z0-9_./-]+", commande)
        assert cibles, "la commande de test ne designe aucune suite : %r" % commande
        for cible in cibles:
            assert os.path.exists(os.path.join(RACINE, cible)), (
                "npm test designe %s, qui n existe pas" % cible)

    def test_le_harnais_javascript_mort_n_est_plus_la(self):
        """Sept serveurs inexistants, un bucket inexistant, zero appelant.

        Supprime le 2026-09-18 plutot que repare : rien ne dependait d un
        resultat vert de sa part.
        """
        for mort in ("tests/mcp/js/test-all-mcp.js",
                     "tests/mcp/js/test-servers.sh"):
            assert not os.path.exists(os.path.join(RACINE, mort)), (
                "%s est revenu" % mort)


# ---------------------------------------------------------------------------
# H12c - le journal doit se tenir lui-meme
#
# logs/latest.json est le seul registre qui dise ce qui reste a faire sur ce
# bateau, et il etait le seul fichier du depot que rien ne verifiait. Le
# 2026-09-20, apres un chantier consacre a la difference entre signaler un
# defaut et le fermer, il portait le defaut 67 dans defects_closed ET dans
# defects_open, le defaut 74 deux fois, et une entree sans identifiant.
#
# Le premier motif que j avais ecrit pour lire ces identifiants etait
# \d+\b. Il ne reconnait pas "20b", un sous-identifiant legitime, et
# comptait donc une entree orpheline de trop. Le motif ci-dessous accepte un
# suffixe de lettre, et deux tests d echantillon le prouvent au lieu de
# l affirmer.
# ---------------------------------------------------------------------------

CHEMIN_JOURNAL = os.path.join(RACINE, "logs", "latest.json")

IDENTIFIANT_DE_DEFAUT = re.compile(r"^\s*(\d+[a-z]?)\b")


def _journal():
    """logs/latest.json, decode."""
    import json as _json
    with open(CHEMIN_JOURNAL, encoding="utf-8") as fichier:
        return _json.load(fichier)


def identifiants_de_defauts(entrees):
    """Identifiants lus en tete d entree, et entrees qui n en portent pas.

    Rend un couple (dictionnaire identifiant -> entrees, liste des
    orphelines). Un identifiant peut porter un suffixe de lettre : 20b est
    un identifiant, pas une entree sans numero.
    """
    vus = {}
    orphelines = []
    for entree in entrees:
        trouve = IDENTIFIANT_DE_DEFAUT.match(str(entree))
        if trouve:
            vus.setdefault(trouve.group(1), []).append(str(entree))
        else:
            orphelines.append(str(entree))
    return vus, orphelines


def incoherences_du_journal(journal):
    """Les trois manieres dont ce registre s est deja contredit."""
    fermes, sans_id_fermes = identifiants_de_defauts(
        journal.get("defects_closed", []))
    ouverts, sans_id_ouverts = identifiants_de_defauts(
        journal.get("defects_open", []))
    return {
        "des_deux_cotes": sorted(set(fermes) & set(ouverts)),
        "en_double": sorted(
            [k for k, v in fermes.items() if len(v) > 1]
            + [k for k, v in ouverts.items() if len(v) > 1]),
        "sans_identifiant": sans_id_fermes + sans_id_ouverts,
    }


class TestLeJournalNeSeContreditPas:
    """Un registre qui se contredit ne dit plus ce qui reste a faire."""

    def test_le_journal_est_lisible_et_porte_les_deux_listes(self):
        journal = _journal()
        for liste in ("defects_closed", "defects_open"):
            assert liste in journal, "logs/latest.json n a plus de %s" % liste
            assert isinstance(journal[liste], list), (
                "%s n est pas une liste" % liste)
            for entree in journal[liste]:
                assert isinstance(entree, str), (
                    "%s contient autre chose qu une chaine : %r" % (liste, entree))

    def test_aucun_defaut_n_est_a_la_fois_ouvert_et_ferme(self):
        """Le cas du defaut 67, le 2026-09-20, apres H12b."""
        vu = incoherences_du_journal(_journal())["des_deux_cotes"]
        assert not vu, (
            "defauts declares ouverts ET fermes : %s" % ", ".join(vu))

    def test_aucun_defaut_n_est_declare_deux_fois(self):
        """Le cas du defaut 74, ferme par H11 puis re-ferme par H11b."""
        vu = incoherences_du_journal(_journal())["en_double"]
        assert not vu, (
            "defauts figurant deux fois dans la meme liste : %s" % ", ".join(vu))

    def test_chaque_defaut_porte_un_identifiant(self):
        """Sans numero, une entree est invisible a tout recoupement."""
        vu = incoherences_du_journal(_journal())["sans_identifiant"]
        assert not vu, (
            "entrees sans identifiant : %s"
            % "; ".join(e[:80] for e in vu))


class TestLeControleDuJournalVoitCeQuIlDoitVoir:
    """Une barriere qui ne rend jamais rouge ne prouve rien.

    Les deux echantillons ci-dessous reproduisent l etat reel du journal au
    commit 9234a33a et une variante, et exigent que le controle les signale.
    """

    def test_le_controle_voit_un_defaut_ouvert_et_ferme_a_la_fois(self):
        echantillon = {
            "defects_closed": [
                "67 harnais JS mort supprime (tests/mcp/js/) - H12b",
                "80 le harnais codait en dur un bucket inexistant - H12b",
            ],
            "defects_open": [
                "67 - tests/mcp/js/test-all-mcp.js teste sept serveurs absents",
                "69 - le conteneur signalk est sorti il y a quatre mois",
            ],
        }
        vu = incoherences_du_journal(echantillon)
        assert vu["des_deux_cotes"] == ["67"], vu
        assert vu["en_double"] == [], vu
        assert vu["sans_identifiant"] == [], vu

    def test_le_controle_voit_un_doublon_une_orpheline_et_accepte_20b(self):
        echantillon = {
            "defects_closed": [
                "74 six commandes visaient un bucket inexistant - H11",
                "74 la documentation citait un bucket inexistant - H11b",
                "20b le compte administrateur Grafana n etait detenu par personne",
                "ProtectHome mediaman.service - unite inexecutable, corrigee en H5d",
            ],
            "defects_open": [],
        }
        vu = incoherences_du_journal(echantillon)
        assert vu["en_double"] == ["74"], vu
        assert vu["des_deux_cotes"] == [], vu
        assert len(vu["sans_identifiant"]) == 1, vu
        assert vu["sans_identifiant"][0].startswith("ProtectHome"), vu


# ---------------------------------------------------------------------------
# H13 - une fermeture doit porter sa preuve
#
# L audit du 2026-09-20 a passe 20 des 34 fermetures declarees a la preuve
# materielle. Dix-neuf tiennent. Quatorze sont infalsifiables : dix disent
# "corrected by addition", c est-a-dire qu un paragraphe a ete ajoute a un
# compte rendu. Rien dans le depot ne peut les confirmer ni les refuter.
#
# Le registre confondait deux choses : changer le systeme, et ecrire a
# propos du systeme. Chaque entree porte desormais " | preuve: ...". Les
# chemins cites doivent exister. Et le nombre de fermetures sans preuve
# materielle ne peut plus augmenter : c est un cliquet, pas un voeu.
# ---------------------------------------------------------------------------

MARQUEUR_PREUVE = " | preuve: "
SANS_PREUVE = "sans preuve materielle"

# Quatorze au 2026-09-20. Ce nombre est un plafond : il peut baisser quand
# une vieille fermeture recoit enfin une preuve, jamais monter.
PLAFOND_SANS_PREUVE = 14

# Le \b final n est pas decoratif : sans lui, l alternative js coupe
# logs/latest.json en logs/latest.js et le controle accuse un chemin
# inexistant. La repetition du 2026-09-20 l a attrape.
CHEMIN_DANS_UNE_PREUVE = re.compile(
    r"[\w./-]+\.(?:py|js|json|md|sh|yml|yaml|service)\b")


def preuve_de(entree):
    """La partie de l entree qui suit le marqueur, ou None."""
    if MARQUEUR_PREUVE not in entree:
        return None
    return entree.split(MARQUEUR_PREUVE, 1)[1].strip()


def fermetures_sans_preuve(journal):
    """Entrees fermees qui ne portent aucun marqueur de preuve."""
    return [e for e in journal.get("defects_closed", [])
            if preuve_de(e) is None]


def chemins_cites_en_preuve(journal):
    """Couples (entree, chemin) pour tous les chemins cites en preuve.

    Le nom porte "en_preuve" parce que chemins_cites existe deja dans ce
    fichier, pour les documents sous garde. La repetition du 2026-09-20 a
    vu la seconde definition ecraser la premiere et faire tomber un test
    ecrit six jours plus tot.
    """
    trouves = []
    for entree in journal.get("defects_closed", []):
        texte = preuve_de(entree)
        if not texte or texte.startswith(SANS_PREUVE):
            continue
        for chemin in CHEMIN_DANS_UNE_PREUVE.findall(texte):
            trouves.append((entree, chemin))
    return trouves


class TestUneFermeturePorteSaPreuve:
    """Le registre doit dire ce qui prouve chaque fermeture."""

    def test_chaque_fermeture_porte_une_preuve(self):
        manquantes = fermetures_sans_preuve(_journal())
        assert not manquantes, (
            "fermetures sans marqueur de preuve : %s"
            % "; ".join(e[:70] for e in manquantes))

    def test_les_chemins_cites_en_preuve_existent(self):
        absents = []
        for entree, chemin in chemins_cites_en_preuve(_journal()):
            if not os.path.exists(os.path.join(RACINE, chemin)):
                absents.append("%s (cite par %s)" % (chemin, entree[:40]))
        assert not absents, (
            "chemins cites en preuve et introuvables : %s" % "; ".join(absents))

    def test_le_nombre_de_fermetures_sans_preuve_ne_monte_pas(self):
        """Un cliquet. Il peut descendre ; il ne remonte pas."""
        journal = _journal()
        combien = sum(1 for e in journal.get("defects_closed", [])
                      if (preuve_de(e) or "").startswith(SANS_PREUVE))
        assert combien <= PLAFOND_SANS_PREUVE, (
            "%d fermetures sans preuve materielle, plafond %d : une fermeture "
            "nouvelle doit citer un fichier, un test ou une ligne"
            % (combien, PLAFOND_SANS_PREUVE))

    def test_le_contrat_historique_compte_ce_qu_il_enumere(self):
        """Le defaut 45 avait aligne le nombre et laisse la liste."""
        chemin = os.path.join(RACINE, "tests", "mcp",
                              "test_phase2_historical_contract.py")
        source = open(chemin, encoding="utf-8").read()
        docstring = source.split('"""')[1]
        enumeres = [l for l in docstring.splitlines()
                    if re.match(r"^\d+\.", l.strip())]
        fonctions = re.findall(r"^def (test_\w+)", source, re.M)
        annonce = re.search(r"Covers (\d+) scenarios across (\d+) test functions",
                            docstring)
        assert annonce, (
            "l en-tete du contrat historique n annonce pas ses deux nombres")
        assert int(annonce.group(1)) == len(enumeres), (
            "en-tete annonce %s scenarios, la liste en compte %d"
            % (annonce.group(1), len(enumeres)))
        assert int(annonce.group(2)) == len(fonctions), (
            "en-tete annonce %s fonctions, le fichier en declare %d"
            % (annonce.group(2), len(fonctions)))


class TestLeControleDesPreuvesVoitCeQuIlDoitVoir:
    """Deux echantillons, parce qu une barriere qui ne rougit jamais ment."""

    def test_le_controle_voit_une_fermeture_sans_preuve(self):
        echantillon = {"defects_closed": [
            "90 corrige par ajout dans le compte rendu de H3b",
            "91 harnais supprime | preuve: tests/mcp/test_h9b_coherence_doc_code.py",
        ]}
        manquantes = fermetures_sans_preuve(echantillon)
        assert len(manquantes) == 1, manquantes
        assert manquantes[0].startswith("90"), manquantes

    def test_le_controle_voit_un_chemin_invente(self):
        echantillon = {"defects_closed": [
            "92 corrige | preuve: mcp/servers/inexistant-server.js",
            "93 note | preuve: sans preuve materielle (annotation d un rapport)",
        ]}
        cites = chemins_cites_en_preuve(echantillon)
        assert [c for _, c in cites] == ["mcp/servers/inexistant-server.js"], cites
        assert not os.path.exists(
            os.path.join(RACINE, "mcp/servers/inexistant-server.js"))


# ---------------------------------------------------------------------------
# H14a - aucun document ne prescrit ce que le depot interdit
#
# Deux fois de suite, le guide de secours a envoye un equipier faire
# exactement ce que le depot interdit. En v1.1 : docker-compose up -d pour
# Signal K, alors que la regle est systemctl uniquement. En v2.0, que j ai
# ecrite moi-meme le 2026-09-20 : systemctl enable --now
# midnight-logsync.timer, alors que l unite porte en capitales, dans son
# propre en-tete, NE PAS REINSTALLER, NE PAS REPARER.
#
# La troisieme fois, un test l attrapera.
# ---------------------------------------------------------------------------

UNITE_DESARMEE = "midnight-logsync"

ARMEMENT = re.compile(
    r"systemctl\s+(?:--\S+\s+)*(?:enable|start|unmask)\b[^\n]*" + UNITE_DESARMEE)

COPIE_EN_MASSE = re.compile(
    r"\bcp\s+[^\n]*etc/systemd/system/\*[^\n]*\s/etc/systemd/system")


# H14a a ferme le defaut 89 avec un controle qui ne regardait que docs/.
# Pendant qu il rendait vert, la commande interdite dormait dans
# etc/systemd/system/README.md, dans un bloc pret a coller, et dans
# l en-tete des deux unites elles-memes. Une mesure plus etroite que son
# nom rassure a tort. Defaut 94.
RACINES_SOUS_GARDE = ("docs", "etc", "scripts")
EXTENSIONS_SOUS_GARDE = (".md", ".sh", ".service", ".timer", ".py")

# Deux racines restent hors perimetre, et ce n est pas un oubli :
#   logs/  : les constats citent le piege mot pour mot ; ce sont des
#            archives de ce qui a ete ecrit, pas des ordres a suivre ;
#   tests/ : les echantillons de ce fichier contiennent la ligne
#            interdite a dessein, pour prouver que le controle la voit.
# Un test verifie que cette exclusion reste bien celle-la, et pas une
# autre qui se serait installee en silence.
RACINES_HORS_GARDE = ("logs", "tests")

# Les quatre fichiers ou la prescription interdite a reellement vecu. Le
# perimetre doit les contenir : c est la seule facon de verifier qu il
# porte son nom.
FICHIERS_OU_LE_PIEGE_A_VECU = (
    "docs/ops/RECOVERY-GUIDE-SAFE.md",
    "etc/systemd/system/README.md",
    "etc/systemd/system/midnight-logsync.service",
    "etc/systemd/system/midnight-logsync.timer",
)


def _fichiers_sous_garde():
    """Tout fichier qu un equipier peut lire et suivre.

    Les .md de la racine, et sous docs/, etc/ et scripts/ ce qui se lit ou
    s execute : .md, .sh, .service, .timer, .py. Un en-tete d unite est un
    document de procedure comme un autre : c est la que la commande
    interdite a survecu a H14a.
    """
    trouves = []
    for nom in sorted(os.listdir(RACINE)):
        if nom.endswith(".md") and os.path.isfile(os.path.join(RACINE, nom)):
            trouves.append(nom)
    for depart in RACINES_SOUS_GARDE:
        racine_depart = os.path.join(RACINE, depart)
        for base, dossiers, fichiers in os.walk(racine_depart):
            dossiers[:] = [d for d in dossiers
                           if d not in (".git", "node_modules", "__pycache__")]
            for nom in fichiers:
                if nom.endswith(EXTENSIONS_SOUS_GARDE):
                    trouves.append(os.path.relpath(
                        os.path.join(base, nom), RACINE))
    return sorted(trouves)


def lignes_logiques(texte):
    """Lignes logiques du shell : une continuation \\ prolonge la precedente.

    Cette fonction n est pas un raffinement. Sans elle, le controle ne voit
    pas le piege qu il est ecrit pour attraper : dans le guide du
    2026-09-20, systemctl enable --now etait sur une ligne et
    midnight-logsync.timer sur la suivante, apres un antislash. Un
    detecteur ligne a ligne rendait vert sur la prescription exacte qu il
    devait refuser. C est l echantillon qui l a montre, pas la relecture.
    """
    logiques = []
    tampon = ""
    debut = None
    for numero, brute in enumerate(texte.splitlines(), 1):
        if not tampon:
            debut = numero
        nue = brute.rstrip()
        if nue.endswith("\\"):
            tampon += nue[:-1] + " "
            continue
        tampon += nue
        logiques.append((debut, tampon))
        tampon = ""
    if tampon:
        logiques.append((debut, tampon))
    return logiques


def _coupables(texte, motif):
    """Lignes logiques ou le motif frappe, citations exclues."""
    trouvees = []
    for numero, ligne in lignes_logiques(texte):
        if ligne.lstrip().startswith(">"):
            continue
        if motif.search(ligne):
            trouvees.append((numero, ligne.strip()))
    return trouvees


def lignes_qui_arment(texte):
    """Prescriptions d armement de l unite desarmee."""
    return _coupables(texte, ARMEMENT)


def lignes_de_copie_en_masse(texte):
    """Copies de tout etc/systemd/system/ sans exclusion."""
    return _coupables(texte, COPIE_EN_MASSE)


class TestAucunDocumentNArmeUneUniteDesarmee:
    """Aucun fichier de procedure ne prescrit ce que le depot interdit."""

    def test_aucun_fichier_sous_garde_n_arme_midnight_logsync(self):
        """Pas seulement docs/ : le piege vivait aussi dans etc/."""
        coupables = []
        for chemin in _fichiers_sous_garde():
            for numero, ligne in lignes_qui_arment(_lire(chemin)):
                coupables.append("%s:%d %s" % (chemin, numero, ligne[:70]))
        assert not coupables, (
            "fichiers prescrivant d armer %s : %s"
            % (UNITE_DESARMEE, "; ".join(coupables)))

    def test_aucun_fichier_sous_garde_ne_copie_les_unites_en_masse(self):
        """Une copie globale reinstallerait l unite desarmee."""
        coupables = []
        for chemin in _fichiers_sous_garde():
            for numero, ligne in lignes_de_copie_en_masse(_lire(chemin)):
                coupables.append("%s:%d %s" % (chemin, numero, ligne[:70]))
        assert not coupables, (
            "copies en masse de etc/systemd/system sans exclusion : %s"
            % "; ".join(coupables))


class TestLeControleDesUnitesVoitCeQuIlDoitVoir:
    """Les deux echantillons sont les lignes reelles du 2026-09-20."""

    def test_le_controle_voit_une_prescription_d_armement(self):
        echantillon = (
            "sudo systemctl daemon-reload\n"
            "sudo systemctl enable --now mediaman.timer \\\n"
            "                            midnight-logs-commit.timer midnight-logsync.timer\n"
            "> Retablir par : sudo systemctl enable --now midnight-logsync.timer\n")
        vues = lignes_qui_arment(echantillon)
        assert len(vues) == 1, vues
        # la ligne logique commence a la ligne 2 et se prolonge sur la 3 :
        # c est exactement la forme que prenait le piege dans le guide.
        assert vues[0][0] == 2, vues
        assert "midnight-logsync.timer" in vues[0][1], vues

    def test_le_controle_voit_une_copie_en_masse_et_epargne_la_boucle(self):
        dangereux = ("sudo cp etc/systemd/system/*.service /etc/systemd/system/\n"
                     "sudo cp etc/systemd/system/*.timer /etc/systemd/system/\n")
        sur = ("for unite in etc/systemd/system/*.service; do\n"
               "  case \"$unite\" in *midnight-logsync*) continue ;; esac\n"
               "  sudo cp \"$unite\" /etc/systemd/system/\n"
               "done\n")
        assert len(lignes_de_copie_en_masse(dangereux)) == 2
        assert lignes_de_copie_en_masse(sur) == []


class TestLePerimetreDeLaMesurePorteSonNom:
    """Ces trois controles portent sur le perimetre, pas sur son contenu.

    H14a a ferme le defaut 89 avec une mesure qui ne regardait que docs/.
    Le contenu de docs/ etait propre ; c est le perimetre qui mentait.
    """

    def test_le_perimetre_couvre_les_fichiers_ou_le_piege_a_deja_vecu(self):
        sous_garde = set(_fichiers_sous_garde())
        oublies = [c for c in FICHIERS_OU_LE_PIEGE_A_VECU
                   if c not in sous_garde]
        assert not oublies, (
            "le perimetre n inclut pas les fichiers ou la prescription "
            "interdite a deja vecu : %s" % "; ".join(oublies))

    def test_le_perimetre_ecarte_les_archives_et_les_echantillons(self):
        """L exclusion doit rester un choix nomme, pas un effet de bord."""
        sous_garde = _fichiers_sous_garde()
        dedans = [c for c in sous_garde
                  if c.split(os.sep)[0] in RACINES_HORS_GARDE]
        assert not dedans, (
            "logs/ et tests/ citent la ligne interdite a dessein : %s"
            % "; ".join(dedans[:3]))
        assert len(sous_garde) > 50, (
            "perimetre suspect : %d fichiers seulement" % len(sous_garde))

    def test_le_controle_voit_les_deux_formes_trouvees_hors_docs(self):
        """Les deux lignes reelles du 2026-09-20, hors de docs/.

        La premiere vient d un bloc ```bash du README des unites, la
        seconde d un commentaire d en-tete d unite. Un controle limite au
        markdown de docs/ n en voyait aucune.
        """
        echantillon = (
            "```bash\n"
            "sudo systemctl enable --now midnight-logsync.timer\n"
            "```\n"
            "# Retablir par :  sudo systemctl enable --now "
            "midnight-logsync.timer\n")
        vues = lignes_qui_arment(echantillon)
        assert [numero for numero, _ in vues] == [2, 4], vues
