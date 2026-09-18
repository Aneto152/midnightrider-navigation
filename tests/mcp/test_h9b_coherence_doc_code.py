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
    "test": "bucket des suites hors ligne",
    "your-bucket": "gabarit a remplacer par le lecteur",
}

ORG_ATTESTEE = "MidnightRider"

MOTIF_ORG = re.compile(
    r"""INFLUX(?:DB)?_(?!CLOUD)[A-Z_]*ORG\s*[:=]\s*["'`]?([A-Za-z0-9_-]+)""")

MOTIFS_BUCKET = (
    re.compile(r"""from\(\s*bucket\s*:\s*["'`]([A-Za-z0-9_-]+)"""),
    re.compile(r"""\bbucket\s*[:=]\s*["'`]([A-Za-z0-9_-]+)["'`]"""),
    re.compile(r"""INFLUX(?:DB)?_(?:CLOUD_)?BUCKET\s*=\s*["'`]?([A-Za-z0-9_-]+)"""),
)


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
                            if nom not in connus:
                                fautes.append("%s:%d -> %s" % (
                                    os.path.relpath(chemin, RACINE), numero, nom))
        assert fautes == [], (
            "buckets cites qui n existent pas sur le serveur : %s" % fautes)

    def test_toute_organisation_citee_est_la_bonne(self):
        """L organisation est unique sur ce serveur : MidnightRider."""
        fautes = []
        for chemin in fichiers_documentation():
            with open(chemin, encoding="utf-8") as f:
                for numero, ligne in enumerate(f, 1):
                    if ligne.lstrip().startswith(">"):
                        continue
                    for nom in MOTIF_ORG.findall(ligne):
                        if nom in ("your-org", "48a34d6463cef7c9"):
                            continue
                        if nom != ORG_ATTESTEE:
                            fautes.append("%s:%d -> %s" % (
                                os.path.relpath(chemin, RACINE), numero, nom))
        assert fautes == [], (
            "organisations citees qui ne sont pas %s : %s"
            % (ORG_ATTESTEE, fautes))

    def test_chaque_bucket_declare_porte_sa_raison(self):
        for table in (BUCKETS_ATTESTES, BUCKETS_FICTIFS_ADMIS):
            for nom, raison in table.items():
                assert raison and len(raison) > 15, (
                    "le bucket %s est declare sans raison" % nom)


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

