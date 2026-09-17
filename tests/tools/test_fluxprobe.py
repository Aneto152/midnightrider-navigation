#!/usr/bin/env python3
"""Tests de non-regression de tools/fluxprobe.py.

Chaque test porte le numero du defaut qu'il verrouille. Ces tests sont
entierement hors ligne : la seule couche reseau (`FluxProbe._send`) est
remplacee par une fonction de test. Aucun InfluxDB n'est requis.
"""

import os
import socket
import sys
import unittest
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.fluxprobe import (  # noqa: E402
    STATE_DATA, STATE_EMPTY, STATE_ERROR, STATE_TIMEOUT,
    AmbiguousResult, ConfigError, EmptyResult, FluxError, FluxProbe,
    FluxResult, IncompleteMeasurement, MalformedRow, Tally,
    as_float, is_ais_context, mask_number, parse_annotated_csv,
    parse_rfc3339, scrub,
)

UNE_TABLE = (
    "#datatype,string,long,dateTime:RFC3339,double,string,string\r\n"
    "#group,false,false,false,false,true,true\r\n"
    "#default,_result,,,,,\r\n"
    ",result,table,_time,_value,_field,context\r\n"
    ",,0,2026-09-07T14:36:21.482Z,45.5,lat,vessels.urn:mrn:signalk:uuid:abc\r\n"
)

DEUX_TABLES = (
    "#datatype,string,long,dateTime:RFC3339,double,string,string\r\n"
    ",result,table,_time,_value,_field,source\r\n"
    ",,0,2026-09-07T13:42:40.000Z,45.5,lat,gps-secours\r\n"
    ",,1,2026-09-07T14:36:21.482Z,45.6,lat,um982\r\n"
)


# Valeur factice, sans aucun pouvoir. Elle porte deliberement le mot
# "dummy" : un litteral long place derriere une variable nommee "token" est
# signale, a juste titre, par scripts/check-staged-secrets.py. Le garde-fou
# a raison et ce n est pas a lui de ceder.
FAUX_JETON = "dummy-valeur-factice-pour-les-tests-h7a"


def sonde(reponse=None, erreur=None, token=None):
    """Construit une sonde dont la couche reseau est remplacee."""
    probe = FluxProbe(url="http://exemple.invalid:8086", org="mr",
                      token=FAUX_JETON if token is None else token,
                      bucket="midnight_rider", default_timeout=1.0)

    def faux_send(flux, timeout):
        if erreur is not None:
            raise erreur
        return reponse

    probe._send = faux_send
    return probe


class TestAnalyseCSV(unittest.TestCase):
    """L'analyse de l'annotated CSV, verrouillee depuis le defaut 5."""

    def test_une_table_une_ligne(self):
        rows = parse_annotated_csv(UNE_TABLE)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["_field"], "lat")
        self.assertEqual(rows[0]["_time"], "2026-09-07T14:36:21.482Z")

    def test_la_colonne_sans_nom_est_ecartee(self):
        rows = parse_annotated_csv(UNE_TABLE)
        self.assertNotIn("", rows[0])

    def test_annotations_et_lignes_blanches_ignorees(self):
        corps = "#datatype,string\n\n,result,table\n,,0\n\n"
        self.assertEqual(len(parse_annotated_csv(corps)), 1)

    def test_fin_de_ligne_unix_acceptee(self):
        self.assertEqual(len(parse_annotated_csv(UNE_TABLE.replace("\r\n", "\n"))), 1)

    def test_corps_vide(self):
        self.assertEqual(parse_annotated_csv(""), ())
        self.assertEqual(parse_annotated_csv(None), ())


class TestEtats(unittest.TestCase):
    """Les quatre etats sont distincts et une erreur parle (defaut 59)."""

    def test_donnees_donnent_DATA(self):
        self.assertEqual(sonde(reponse=UNE_TABLE).query("x").state, STATE_DATA)

    def test_reponse_sans_ligne_donne_EMPTY_et_non_ERROR(self):
        resultat = sonde(reponse="#datatype,string\n").query("x")
        self.assertEqual(resultat.state, STATE_EMPTY)
        self.assertFalse(resultat.failed)

    def test_delai_depasse_donne_TIMEOUT_avec_message(self):
        resultat = sonde(erreur=socket.timeout()).query("x")
        self.assertEqual(resultat.state, STATE_TIMEOUT)
        self.assertTrue(resultat.detail)

    def test_erreur_http_donne_ERROR_avec_le_corps(self):
        erreur = urllib.error.HTTPError("http://x", 422, "Unprocessable",
                                        {}, None)
        resultat = sonde(erreur=erreur).query("x")
        self.assertEqual(resultat.state, STATE_ERROR)
        self.assertIn("422", resultat.detail)

    def test_exception_inattendue_donne_ERROR_nomme(self):
        resultat = sonde(erreur=ValueError("cassure")).query("x")
        self.assertEqual(resultat.state, STATE_ERROR)
        self.assertIn("ValueError", resultat.detail)
        self.assertIn("cassure", resultat.detail)

    def test_un_etat_en_echec_sans_message_est_refuse(self):
        with self.assertRaises(FluxError):
            FluxResult(STATE_ERROR, (), "")

    def test_etat_inconnu_refuse(self):
        with self.assertRaises(FluxError):
            FluxResult("PEUT-ETRE", ())


class TestDefaut60(unittest.TestCase):
    """Interdiction de lire rows[0] d'une reponse multi-series."""

    def test_deux_tables_comptent_deux_series(self):
        resultat = sonde(reponse=DEUX_TABLES).query("x")
        self.assertEqual(resultat.series_count, 2)

    def test_single_row_refuse_de_choisir(self):
        with self.assertRaises(AmbiguousResult):
            sonde(reponse=DEUX_TABLES).query("x").single_row()

    def test_single_row_accepte_une_seule_ligne(self):
        ligne = sonde(reponse=UNE_TABLE).query("x").single_row()
        self.assertEqual(ligne["_value"], "45.5")

    def test_single_row_leve_si_vide(self):
        with self.assertRaises(EmptyResult):
            sonde(reponse="").query("x").single_row()

    def test_latest_row_ignore_l_ordre_du_document(self):
        """Le coeur du defaut 60 : rows[0] n'est pas le plus recent."""
        resultat = sonde(reponse=DEUX_TABLES).query("x")
        self.assertEqual(resultat.rows[0]["_time"], "2026-09-07T13:42:40.000Z")
        self.assertEqual(resultat.latest_row()["_time"],
                         "2026-09-07T14:36:21.482Z")

    def test_latest_row_leve_si_horodatage_illisible(self):
        corps = ",result,table,_time,_value\n,,0,pas-une-date,1\n"
        with self.assertRaises(MalformedRow):
            sonde(reponse=corps).query("x").latest_row()

    def test_require_single_series_refuse_deux_series(self):
        with self.assertRaises(AmbiguousResult):
            sonde(reponse=DEUX_TABLES).query("x").require_single_series()

    def test_require_single_series_accepte_une_serie(self):
        resultat = sonde(reponse=UNE_TABLE).query("x").require_single_series()
        self.assertEqual(resultat.series_count, 1)

    def test_require_state_expose_le_message_reel(self):
        resultat = sonde(erreur=ValueError("motif")).query("x")
        with self.assertRaises(FluxError) as piege:
            resultat.require_state(STATE_DATA)
        self.assertIn("motif", str(piege.exception))


class TestDefaut59(unittest.TestCase):
    """Le denominateur est le nombre de tentatives, pas de succes."""

    def test_rate_refuse_quand_une_tentative_a_echoue(self):
        compteur = Tally("rejeu racing.js")
        compteur.record(sonde(reponse=UNE_TABLE).query("x"))
        for _ in range(11):
            compteur.record(sonde(erreur=ValueError("boum")).query("x"))
        with self.assertRaises(IncompleteMeasurement):
            compteur.rate(1)

    def test_le_message_dit_combien_de_tentatives_ont_echoue(self):
        compteur = Tally("campagne")
        compteur.record(sonde(erreur=ValueError("boum")).query("x"))
        try:
            compteur.rate(0)
            self.fail("un taux a ete produit malgre un echec")
        except IncompleteMeasurement as erreur:
            self.assertIn("boum", str(erreur))

    def test_denominateur_egal_aux_tentatives(self):
        compteur = Tally("campagne")
        for _ in range(3):
            compteur.record(sonde(reponse=UNE_TABLE).query("x"))
        compteur.record(sonde(reponse="").query("x"))
        self.assertEqual(compteur.attempts, 4)
        self.assertEqual(compteur.rate(3), "3/4")

    def test_EMPTY_n_est_pas_un_echec(self):
        compteur = Tally("campagne")
        compteur.record(sonde(reponse="").query("x"))
        self.assertEqual(compteur.failures, 0)
        self.assertEqual(compteur.rate(0), "0/1")

    def test_summary_montre_toujours_les_quatre_etats(self):
        compteur = Tally("campagne")
        compteur.record(sonde(erreur=socket.timeout()).query("x"))
        texte = compteur.summary()
        for etat in ("DATA", "EMPTY", "TIMEOUT", "ERROR"):
            self.assertIn(etat, texte)

    def test_allow_partial_est_explicite(self):
        compteur = Tally("campagne")
        compteur.record(sonde(erreur=ValueError("boum")).query("x"))
        self.assertEqual(compteur.rate(0, allow_partial=True), "0/1")


class TestSecrets(unittest.TestCase):
    """Aucun jeton ne doit sortir, jamais."""

    def test_le_jeton_n_apparait_pas_dans_la_requete_conservee(self):
        jeton = FAUX_JETON
        probe = sonde(reponse=UNE_TABLE, token=jeton)
        resultat = probe.query('from(bucket:"b") // %s' % jeton)
        self.assertNotIn(jeton, resultat.query)
        self.assertIn("[REDACTED]", resultat.query)

    def test_le_jeton_n_apparait_pas_dans_le_message_d_erreur(self):
        jeton = FAUX_JETON
        probe = sonde(erreur=ValueError(jeton), token=jeton)
        self.assertNotIn(jeton, probe.query("x").detail)

    def test_scrub_ignore_les_chaines_courtes(self):
        self.assertEqual(scrub("abc def", ["abc"]), "abc def")

    def test_empreinte_refusee_pour_un_jeton_court(self):
        probe = FluxProbe("u", "o", "court", "b")
        self.assertIn("trop court", probe.token_fingerprint())

    def test_empreinte_stable_pour_un_jeton_long(self):
        probe = FluxProbe("u", "o", "z" * 88, "b")
        self.assertEqual(len(probe.token_fingerprint()), 16)

    def test_from_env_nomme_les_variables_sans_les_valeurs(self):
        with self.assertRaises(ConfigError) as piege:
            FluxProbe.from_env({"INFLUX_URL": "http://x", "INFLUX_TOKEN": "t"})
        message = str(piege.exception)
        self.assertIn("INFLUX_ORG", message)
        self.assertIn("INFLUX_BUCKET", message)
        self.assertNotIn("http://x", message)

    def test_from_env_complet(self):
        probe = FluxProbe.from_env({"INFLUX_URL": "http://x/", "INFLUX_TOKEN": "t",
                                    "INFLUX_ORG": "o", "INFLUX_BUCKET": "b"})
        self.assertEqual(probe.url, "http://x")
        self.assertEqual(probe.bucket, "b")


class TestConversions(unittest.TestCase):
    """Horodatages, valeurs et masquage."""

    def test_nanosecondes_acceptees(self):
        stamp = parse_rfc3339("2026-09-07T14:36:21.482193472Z")
        self.assertIsNotNone(stamp)
        self.assertEqual(stamp.microsecond, 482193)

    def test_sans_fraction(self):
        self.assertIsNotNone(parse_rfc3339("2026-09-07T14:36:21Z"))

    def test_chaine_invalide_donne_None_sans_exception(self):
        self.assertIsNone(parse_rfc3339("hier"))
        self.assertIsNone(parse_rfc3339(""))
        self.assertIsNone(parse_rfc3339(None))

    def test_as_float_rejette_non_fini(self):
        self.assertIsNone(as_float("NaN"))
        self.assertIsNone(as_float("+Inf"))
        self.assertIsNone(as_float("abc"))
        self.assertIsNone(as_float(""))

    def test_as_float_preserve_zero(self):
        self.assertEqual(as_float("0"), 0.0)
        self.assertEqual(as_float("0.0"), 0.0)

    def test_mask_number_tronque(self):
        self.assertEqual(mask_number("45.123456"), "45.1<masque>")
        self.assertEqual(mask_number("45"), "45")
        self.assertEqual(mask_number("45.1"), "45.1")


class TestClassementAIS(unittest.TestCase):
    """is_ais_context doit rester aligne sur Classifier.classify()."""

    def test_cible_navire_ais(self):
        self.assertTrue(is_ais_context("vessels.urn:mrn:imo:mmsi:368217460"))

    def test_balise_aton(self):
        self.assertTrue(is_ais_context("atons.urn:mrn:imo:mmsi:990901713"))

    def test_uuid_signalk_n_est_pas_ais(self):
        self.assertFalse(
            is_ais_context("vessels.urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f"))

    def test_vide_et_none(self):
        self.assertFalse(is_ais_context(""))
        self.assertFalse(is_ais_context(None))

    def test_non_ais_ne_veut_pas_dire_notre_bateau(self):
        """Garde-fou de portee : la fonction ne designe pas le bateau."""
        self.assertFalse(is_ais_context("vessels.urn:mrn:signalk:uuid:autre"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
