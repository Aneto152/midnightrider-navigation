#!/usr/bin/env python3
"""H9 - collect_current : le direct est l historique dont la borne haute est maintenant.

Le collecteur avait deux corps de collecte. Celui de collect_historical
validait les quatre champs, leurs unites et leurs domaines ; celui de
collect() enchainait trois appels independants et acceptait un resultat
partiel. La qualite de la collecte dependait donc de la methode appelee.

Depuis le 2026-09-18 il n y a qu un corps, _collect_snapshot, et deux
entrees minces. Ces tests verifient que les deux entrees ne different que
par les deux choses par lesquelles elles ont le droit de differer :
  - qui choisit la borne haute de l intervalle ;
  - si l age du fait compte.

Ils verifient aussi ce que Denis a demande le 2026-09-18 : que le jeu de
donnees historique serve de banc d essai au chemin du direct. C est
reference_time qui le permet, cote client, sans qu aucune horloge ne soit
trompee nulle part.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from mediaman.mcp_collector import MCPCollector, CollectionStatus  # noqa: E402

INSTANT = "2026-09-07T14:36:24.298Z"

FAITS = {
    "latitude": 41.1111111,
    "longitude": -72.2222222,
    "speed_over_ground_ms": 3.3333,
    "course_over_ground_degrees": 70.7316,
}
UNITES = {
    "latitude": "degrees",
    "longitude": "degrees",
    "speed_over_ground_ms": "m_per_s",
    "course_over_ground_degrees": "degrees_true",
}


class ClientFactice:
    """Faux client MCP : enregistre l appel et rend une reponse complete."""

    def __init__(self, source_timestamp=INSTANT):
        self.appels = []
        self.source_timestamp = source_timestamp

    def call_tool(self, nom, arguments=None):
        self.appels.append((nom, dict(arguments or {})))
        return {
            "result": {
                "success": True,
                "status": "COMPLETE",
                "facts": dict(FAITS),
                "units": dict(UNITES),
                "source_timestamp": self.source_timestamp,
                "bounded_skew_ms": 1,
            },
            "observed_at": self.source_timestamp,
        }


def _collecteur(client, reference_time=None):
    return MCPCollector(client=client, race_id="essai",
                        reference_time=reference_time)


def test_collect_current_adresse_la_porte_de_plage():
    """Le direct passe par get_snapshot, avec deux bornes explicites."""
    client = ClientFactice()
    resultat = _collecteur(client, "2026-09-07T14:36:26Z").collect_current()

    assert resultat.status == CollectionStatus.COMPLETE, resultat.errors
    assert len(client.appels) == 1
    nom, arguments = client.appels[0]
    assert nom == "racing.get_snapshot"
    assert set(arguments) == {"start_utc", "end_utc"}
    assert arguments["end_utc"] == "2026-09-07T14:36:26Z"
    assert arguments["start_utc"] == "2026-09-07T14:35:56Z"


def test_la_fenetre_du_direct_est_reglable():
    """La fenetre est un parametre, pas une constante cachee."""
    client = ClientFactice()
    _collecteur(client, "2026-09-07T14:36:26Z").collect_current(window_seconds=120)
    _, arguments = client.appels[0]
    assert arguments["start_utc"] == "2026-09-07T14:34:26Z"


def test_une_fenetre_aberrante_est_refusee_sans_appel():
    """Une fenetre hors bornes ne doit meme pas atteindre le serveur."""
    for fenetre in (0, -1, 3601, "30", 1.5, True):
        client = ClientFactice()
        resultat = _collecteur(client, "2026-09-07T14:36:26Z").collect_current(
            window_seconds=fenetre)
        assert resultat.status == CollectionStatus.FAILED, fenetre
        assert client.appels == [], (
            "fenetre %r : le serveur a ete appele malgre tout" % (fenetre,))


def test_le_jeu_historique_sert_de_banc_au_chemin_du_direct():
    """Le coeur de la demande de Denis du 2026-09-18.

    reference_time recule la borne haute jusqu a un instant reellement
    enregistre. Le code execute est celui du direct, ligne pour ligne, et il
    travaille sur des donnees reelles. Aucune horloge n est trompee : le
    serveur ne demande jamais l heure, c est l appelant qui la fournit.
    """
    client = ClientFactice()
    resultat = _collecteur(client, "2026-09-07T14:36:26Z").collect_current()

    assert resultat.status == CollectionStatus.COMPLETE, resultat.errors
    assert len(resultat.facts) == 4
    _, arguments = client.appels[0]
    assert arguments["end_utc"].startswith("2026-09-07")


def test_un_fait_trop_vieux_rend_partial_et_non_complete():
    """Une position perimee decrit un bateau qui n y est plus."""
    client = ClientFactice(source_timestamp="2026-09-07T14:00:00Z")
    resultat = _collecteur(client, "2026-09-07T14:36:26Z").collect_current()

    assert resultat.status == CollectionStatus.PARTIAL, resultat.status
    assert len(resultat.facts) == 4, "les faits restent disponibles"
    assert any("stale" in a for a in resultat.warnings), resultat.warnings
    assert resultat.facts[0].provenance.validation_status == "stale"


def test_l_historique_n_a_pas_de_limite_de_fraicheur():
    """Un fait ancien est le but d une collecte historique, pas un defaut."""
    client = ClientFactice(source_timestamp="2026-09-07T14:00:00Z")
    resultat = _collecteur(client, "2026-09-18T12:00:00Z").collect_historical(
        as_of_utc="2026-09-07T14:36:26Z", window_seconds=60)

    assert resultat.status == CollectionStatus.COMPLETE, resultat.errors
    assert client.appels[0][0] == "racing.get_historical_snapshot"
    assert resultat.facts[0].provenance.freshness_limit_seconds is None
    assert resultat.facts[0].provenance.validation_status == "valid"


def test_les_deux_entrees_produisent_les_memes_faits():
    """Meme charge utile, memes faits : le corps est bien partage."""
    client_direct = ClientFactice()
    direct = _collecteur(client_direct, "2026-09-07T14:36:26Z").collect_current()
    client_passe = ClientFactice()
    passe = _collecteur(client_passe, "2026-09-18T12:00:00Z").collect_historical(
        as_of_utc="2026-09-07T14:36:26Z", window_seconds=30)

    valeurs_direct = [(f.field_name, f.value, f.unit) for f in direct.facts]
    valeurs_passe = [(f.field_name, f.value, f.unit) for f in passe.facts]
    assert valeurs_direct == valeurs_passe

    # Les deux seules differences legitimes, et elles sont ici.
    assert direct.facts[0].provenance.tool_public_id == "racing.get_snapshot"
    assert passe.facts[0].provenance.tool_public_id == "racing.get_historical_snapshot"
    assert direct.facts[0].provenance.freshness_limit_seconds == 30
    assert passe.facts[0].provenance.freshness_limit_seconds is None


def test_le_contrat_des_unites_du_defaut_63_vaut_aussi_pour_le_direct():
    """Une unite fausse fait echouer la collecte, quelle que soit l entree."""
    class ClientMenteur(ClientFactice):
        def call_tool(self, nom, arguments=None):
            reponse = super().call_tool(nom, arguments)
            reponse["result"]["units"]["course_over_ground_degrees"] = "radians"
            return reponse

    resultat = _collecteur(ClientMenteur(), "2026-09-07T14:36:26Z").collect_current()
    assert resultat.status == CollectionStatus.FAILED
    assert any("unit mismatch" in e for e in resultat.errors), resultat.errors


# ======================================================================
# Proprietes portees depuis tests/mediaman/test_mcp_collector.py
#
# Ce fichier de 627 lignes et 32 tests portait entierement sur collect(),
# le chemin que racing.js n a jamais su servir. Il a ete supprime le
# 2026-09-18 avec H9. Vingt-quatre de ses tests verifiaient une semantique
# qui n existe plus - la collecte outil par outil, et donc la reussite
# partielle d un outil sur trois - et n avaient rien a proteger une fois
# l appel rendu atomique.
#
# Les huit ci-dessous sont portes parce que les proprietes qu ils
# protegent, elles, restent vraies et valent pour n importe quel chemin :
# la confidentialite des coordonnees dans les journaux et dans le contexte
# transmis au modele, l absence de tout acces direct a Signal K, et le
# traitement des horodatages aberrants. Les perdre aurait ete perdre des
# garanties de confidentialite, pas du confort.
# ======================================================================

import json
import logging
import tempfile
from pathlib import Path

LATITUDE_PRECISE = 41.123456789
LONGITUDE_PRECISE = -73.987654321


class ClientPrecis(ClientFactice):
    """Rend des coordonnees a neuf decimales, pour les traquer ensuite."""

    def call_tool(self, nom, arguments=None):
        reponse = super().call_tool(nom, arguments)
        reponse["result"]["facts"]["latitude"] = LATITUDE_PRECISE
        reponse["result"]["facts"]["longitude"] = LONGITUDE_PRECISE
        return reponse


def test_les_valeurs_de_position_restent_exactes():
    """La confidentialite ne doit pas se payer en precision."""
    resultat = _collecteur(ClientPrecis(), "2026-09-07T14:36:26Z").collect_current()
    assert resultat.status == CollectionStatus.COMPLETE, resultat.errors
    valeurs = {f.field_name: f.value for f in resultat.facts}
    assert valeurs["latitude"] == LATITUDE_PRECISE
    assert valeurs["longitude"] == LONGITUDE_PRECISE


def test_le_journal_ne_contient_aucune_coordonnee():
    """Aucune coordonnee exacte ne doit atteindre un fichier de journal."""
    with tempfile.TemporaryDirectory() as dossier:
        fichier = Path(dossier) / "essai.log"
        poignee = logging.FileHandler(fichier)
        collecteur = _collecteur(ClientPrecis(), "2026-09-07T14:36:26Z")
        collecteur.logger.addHandler(poignee)
        try:
            collecteur.collect_current()
        finally:
            collecteur.logger.removeHandler(poignee)
            poignee.close()
        journal = fichier.read_text()

    assert "STARTUP" in journal, "le demarrage doit rester tracable"
    assert "41.123456789" not in journal
    assert "73.987654321" not in journal


def test_le_contexte_du_modele_supprime_la_latitude():
    """Le modele redige sans jamais recevoir la position exacte."""
    resultat = _collecteur(ClientPrecis(), "2026-09-07T14:36:26Z").collect_current()
    contexte = resultat.to_llm_context()
    latitude = [f for f in contexte["facts"] if f["field_name"] == "latitude"][0]
    assert latitude["value"] == "<coordinate suppressed>"


def test_le_contexte_du_modele_supprime_la_longitude():
    resultat = _collecteur(ClientPrecis(), "2026-09-07T14:36:26Z").collect_current()
    contexte = resultat.to_llm_context()
    longitude = [f for f in contexte["facts"] if f["field_name"] == "longitude"][0]
    assert longitude["value"] == "<coordinate suppressed>"


def test_aucune_coordonnee_dans_le_contexte_serialise():
    """Verification par le texte, et non champ par champ.

    Un futur champ ajoute au contexte pourrait laisser fuir la position
    sans qu aucune assertion nommee ne s en apercoive. Celle-ci cherche la
    coordonnee dans le JSON entier.
    """
    resultat = _collecteur(ClientPrecis(), "2026-09-07T14:36:26Z").collect_current()
    texte = json.dumps(resultat.to_llm_context(), default=str)
    assert "41.123456789" not in texte
    assert "73.987654321" not in texte


def test_le_collecteur_n_instancie_aucun_client_de_lui_meme():
    """Le client est injecte : aucun acces direct a Signal K n est possible."""
    client = ClientFactice()
    collecteur = _collecteur(client, "2026-09-07T14:36:26Z")
    assert collecteur.client is client
    collecteur.collect_current()
    assert len(client.appels) == 1, (
        "le collecteur a parle a autre chose qu au client injecte")


def test_un_horodatage_dans_le_futur_est_traite_comme_manquant():
    """Une donnee datee de demain n est pas fraiche, elle est suspecte."""
    client = ClientFactice(source_timestamp="2026-09-07T15:36:26Z")
    resultat = _collecteur(client, "2026-09-07T14:36:26Z").collect_current()
    assert resultat.facts[0].provenance.validation_status == "missing"
    assert resultat.status == CollectionStatus.PARTIAL


def test_un_horodatage_malforme_ne_leve_pas_d_exception():
    """Une chaine illisible degrade le statut, elle n interrompt rien."""
    client = ClientFactice(source_timestamp="pas-un-horodatage")
    resultat = _collecteur(client, "2026-09-07T14:36:26Z").collect_current()
    assert resultat.facts[0].provenance.validation_status == "missing"
    assert resultat.status == CollectionStatus.PARTIAL
