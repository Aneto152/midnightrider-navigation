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

