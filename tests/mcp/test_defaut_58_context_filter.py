"""Defaut 58 - le filtre de contexte de mcp/servers/racing.js.

Ces tests lancent le VRAI serveur racing.js contre un faux InfluxDB qui
LIT la requete Flux recue et repond en consequence, comme le ferait le
vrai moteur. Le faux des tests existants renvoie la meme reponse quelle
que soit la requete : il ne peut donc pas distinguer une requete filtree
d'une requete non filtree. C'est precisement ce qu'il n'a pas vu.

Les valeurs ci-dessous sont FICTIVES et le restent volontairement. Ce test
n a pas besoin de la position reelle du bateau : il lui faut deux jeux de
valeurs distincts, l un attribue a notre contexte et l autre a une cible
AIS qui ecrit apres nous. La politique du depot, posee dans
docs/DECISIONS/MEDIAMAN-HISTORICAL-DRY-RUN.md, est que les valeurs de faits
n y sont pas consignees.

  notre bateau  41.1111111 / -72.2222222   SOG 0      COG 0
  cible AIS     41.3333333 / -72.4444444   SOG 6.66   COG 2.2222

Le tag `self` n'existe que sur nos propres lignes, avec la seule valeur
"true" ; les 3990 contextes AIS ne portent aucun tag `self`. La cible AIS
a ecrit APRES nous : sans filtre, c'est elle qui gagne le last().
"""

import json
import os
import re
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

# (bateau, cible AIS) pour chaque couple mesure/champ interroge par racing.js
VALEURS = {
    ("navigation.position", "lat"): ("41.1111111", "41.3333333"),
    ("navigation.position", "lon"): ("-72.2222222", "-72.4444444"),
    ("navigation.speedOverGround", "value"): ("0", "6.66"),
    ("navigation.courseOverGroundTrue", "value"): ("0", "2.2222"),
}
# Le bateau ecrit avant la cible AIS : c'est tout le piege du last().
HEURE_BATEAU = "2026-09-07T14:36:24.298Z"
HEURE_AIS = "2026-09-07T14:36:24.900Z"
FILTRE_ATTENDU = 'r.self == "true"'


def csv_annote(heure, valeur, champ, mesure, debut, fin):
    """Reproduit un annotated CSV InfluxDB 2.x, terminaisons CRLF comprises."""
    return (
        "#group,false,false,true,true,false,false,true,true\r\n"
        "#datatype,string,long,dateTime:RFC3339,dateTime:RFC3339,"
        "dateTime:RFC3339Nano,double,string,string\r\n"
        "#default,_result,,,,,,,\r\n"
        ",result,table,_start,_stop,_time,_value,_field,_measurement\r\n"
        ",,0," + debut + "," + fin + "," + heure + ","
        + valeur + "," + champ + "," + mesure + "\r\n"
        "\r\n"
    )


class FauxInfluxContextuel(BaseHTTPRequestHandler):
    """Faux InfluxDB qui repond en fonction du contenu de la requete Flux."""

    corps_recus = []
    servir_ais = True
    vide_si_filtre = False

    @classmethod
    def reinitialiser(cls):
        cls.corps_recus = []
        cls.servir_ais = True
        cls.vide_si_filtre = False

    @classmethod
    def repondre(cls, flux):
        mesure = None
        trouve = re.search(r'r\._measurement == "([^"]+)"', flux)
        if trouve:
            mesure = trouve.group(1)
        champ = None
        trouve = re.search(r'r\._field == "([^"]+)"', flux)
        if trouve:
            champ = trouve.group(1)
        if (mesure, champ) not in VALEURS:
            return ""
        filtre = FILTRE_ATTENDU in flux
        if filtre and cls.vide_si_filtre:
            return ""
        bateau, ais = VALEURS[(mesure, champ)]
        if filtre or not cls.servir_ais:
            valeur, heure = bateau, HEURE_BATEAU
        else:
            valeur, heure = ais, HEURE_AIS
        return csv_annote(heure, valeur, champ, mesure,
                          "2026-09-07T14:31:25.000Z", "2026-09-07T14:36:25.000Z")

    def do_POST(self):
        taille = int(self.headers.get("Content-Length", 0))
        flux = self.rfile.read(taille).decode("utf-8")
        FauxInfluxContextuel.corps_recus.append(flux)
        corps = FauxInfluxContextuel.repondre(flux).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, format, *args):
        return


def port_libre():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as prise:
        prise.bind(("127.0.0.1", 0))
        return prise.getsockname()[1]


@pytest.fixture
def faux_influx():
    FauxInfluxContextuel.reinitialiser()
    port = port_libre()
    serveur = HTTPServer(("127.0.0.1", port), FauxInfluxContextuel)
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    yield "http://127.0.0.1:%d" % port
    serveur.shutdown()


@pytest.fixture
def serveur_racing(faux_influx):
    racine = Path(__file__).parent.parent.parent
    racing = racine / "mcp" / "servers" / "racing.js"
    if not racing.exists():
        pytest.skip("racing.js absent")
    env = os.environ.copy()
    env["INFLUX_URL"] = faux_influx
    env["INFLUX_TOKEN"] = "jeton-de-test-sans-valeur"
    env["INFLUX_ORG"] = "MidnightRider"
    env["INFLUX_BUCKET"] = "midnight_rider"
    processus = subprocess.Popen(
        ["node", str(racing)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env, text=True, bufsize=1)
    time.sleep(0.5)
    yield processus
    try:
        processus.terminate()
        processus.wait(timeout=2)
    except subprocess.TimeoutExpired:
        processus.kill()


def appel(processus, methode, params=None, identifiant=1):
    requete = {"jsonrpc": "2.0", "id": identifiant, "method": methode}
    if params:
        requete["params"] = params
    processus.stdin.write(json.dumps(requete) + "\n")
    processus.stdin.flush()
    ligne = ""
    debut = time.time()
    while True:
        if time.time() - debut > 8:
            raise TimeoutError("pas de reponse MCP a %s" % methode)
        caractere = processus.stdout.read(1)
        if not caractere:
            raise EOFError("racing.js s'est arrete")
        ligne += caractere
        if ligne.endswith("\n"):
            break
    return json.loads(ligne.strip())


def snapshot(objet):
    """Retrouve la charge utile du snapshot ou qu'elle soit dans l'enveloppe."""
    if isinstance(objet, dict):
        if "facts" in objet and "source_timestamp" in objet:
            return objet
        for valeur in objet.values():
            trouve = snapshot(valeur)
            if trouve is not None:
                return trouve
    elif isinstance(objet, list):
        for valeur in objet:
            trouve = snapshot(valeur)
            if trouve is not None:
                return trouve
    elif isinstance(objet, str):
        candidat = objet.strip()
        if candidat.startswith("{"):
            try:
                return snapshot(json.loads(candidat))
            except (ValueError, TypeError):
                return None
    return None


def demander_snapshot(processus, identifiant=2):
    appel(processus, "initialize")
    return appel(processus, "tools/call", {
        "name": "get_historical_snapshot",
        "arguments": {"as_of_utc": "2026-09-07T14:36:25.000Z",
                      "window_seconds": 300},
    }, identifiant=identifiant)


def test_le_filtre_self_est_envoye_et_precede_keep(serveur_racing):
    """Le filtre doit etre present ET au-dessus de keep(), qui detruit le tag.

    Place sous keep(columns: ["_time", "_value"]), le filtre ne verrait plus
    aucune colonne `self` : il ne filtrerait rien et retablirait le defaut 58
    en silence. L'ordre est donc une assertion a part entiere.
    """
    demander_snapshot(serveur_racing)
    corps = FauxInfluxContextuel.corps_recus
    assert len(corps) == 4, "racing.js doit poser 4 requetes, pas %d" % len(corps)
    for flux in corps:
        assert FILTRE_ATTENDU in flux, "filtre de contexte absent :\n" + flux
        assert "keep(" in flux, flux
        assert flux.index(FILTRE_ATTENDU) < flux.index("keep("), (
            "le filtre self est APRES keep(), il ne filtre donc rien :\n" + flux)


def test_la_cible_ais_plus_recente_est_ignoree(serveur_racing):
    """Le coeur du defaut 58 : une cible AIS qui ecrit apres nous.

    Sans filtre, les quatre faits publies etaient ceux du mmsi 368111560.
    """
    reponse = demander_snapshot(serveur_racing)
    charge = snapshot(reponse)
    assert charge is not None, json.dumps(reponse, default=str)
    assert charge.get("success") is True, json.dumps(charge, default=str)
    faits = charge["facts"]
    assert abs(faits["latitude"] - 41.1111111) < 1e-7, faits
    assert abs(faits["longitude"] - (-72.2222222)) < 1e-7, faits
    assert faits["speed_over_ground_ms"] == 0, faits
    assert faits["course_over_ground_degrees"] == 0, faits
    # La preuve en negatif : aucune valeur de la cible AIS ne doit survivre.
    for interdit in (41.3333333, -72.4444444, 6.66, 2.2222):
        assert interdit not in faits.values(), (
            "valeur de la cible AIS publiee comme fait du bateau : %r" % interdit)


def test_aucune_source_n_est_epinglee(serveur_racing):
    """Les trois chemins portent N2K.0, N2K.1 et N2K.2 (mesure 2026-09-17).

    Les deux Vulcan 7 ne sont pas toujours allumes tous les deux : preferer
    une source nommee rendrait MediaMan aveugle le jour ou elle se taît.
    """
    demander_snapshot(serveur_racing)
    for flux in FauxInfluxContextuel.corps_recus:
        for interdit in ("N2K.0", "N2K.1", "N2K.2", 'r.source ==',
                         "sourcePriorities"):
            assert interdit not in flux, (
                "source epinglee dans la requete : %s\n%s" % (interdit, flux))


def test_les_quatre_faits_portent_l_heure_du_bateau(serveur_racing):
    reponse = demander_snapshot(serveur_racing)
    charge = snapshot(reponse)
    assert charge is not None, json.dumps(reponse, default=str)
    assert len(charge["fact_timestamps"]) == 4, charge
    for nom, heure in charge["fact_timestamps"].items():
        assert heure.startswith("2026-09-07T14:36:24.29"), (nom, heure)
    assert charge["bounded_skew_ms"] == 0, charge
    assert charge["source_timestamp"].endswith("Z"), charge


def test_sans_cible_ais_le_resultat_est_identique(serveur_racing):
    """Non-regression : quand nous sommes seuls, le filtre ne change rien."""
    FauxInfluxContextuel.servir_ais = False
    reponse = demander_snapshot(serveur_racing)
    charge = snapshot(reponse)
    assert charge is not None, json.dumps(reponse, default=str)
    assert charge.get("success") is True, json.dumps(charge, default=str)
    assert abs(charge["facts"]["latitude"] - 41.1111111) < 1e-7, charge


def test_si_le_filtre_ne_rend_rien_le_snapshot_est_incomplet(serveur_racing):
    """Repli sur : mieux vaut rien annoncer qu'annoncer la position d'autrui.

    Si nos propres lignes manquent dans la fenetre, racing.js doit declarer
    la collecte incomplete, et surtout PAS se rabattre sur une cible AIS.
    """
    FauxInfluxContextuel.vide_si_filtre = True
    reponse = demander_snapshot(serveur_racing)
    charge = snapshot(reponse)
    brut = json.dumps(reponse, default=str)
    assert charge is None or charge.get("success") is not True, brut
    assert "incomplete" in brut.lower(), brut
    for interdit in ("41.3333333", "-72.4444444", "6.66", "2.2222"):
        assert interdit not in brut, (
            "valeur AIS publiee alors que le bateau est absent : " + interdit)
