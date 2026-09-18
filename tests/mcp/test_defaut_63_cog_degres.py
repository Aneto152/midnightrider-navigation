#!/usr/bin/env python3
"""Defaut 63 - le cap est publie en degres vrais, et les unites sont declarees.

Signal K sert navigation.courseOverGroundTrue en RADIANS : c est une unite SI
et c est la convention du bus. Le serveur MCP publiait cette valeur telle
quelle sous la cle course_over_ground_degrees ; le collecteur l etiquetait
unit="degrees_true" et l article ecrivait "Cap: {valeur}deg". Un bateau au cap
198 degres etait donc annonce a 3,45 degres. Trois validations successives
laissaient passer l erreur, parce que tout intervalle plausible en degres
contient l intervalle des radians : 0 a 360 contient 0 a 6,28.

Ces tests verrouillent cinq choses :
  - la conversion a lieu, exactement une fois, dans le serveur ;
  - zero radian reste zero degre, et 2*PI vaut 360 ;
  - une valeur hors du domaine radian fait echouer la collecte bruyamment,
    au lieu de publier un cap absurde ;
  - la reponse declare ses unites, pour que ce defaut ne puisse pas revenir
    en silence ;
  - le filtre de contexte du defaut 58 est toujours present dans les quatre
    requetes, et toujours AVANT le keep().

Le faux InfluxDB LIT la requete Flux et repond selon la mesure et le champ
demandes. C est indispensable : un faux serveur qui repond la meme chose a
toutes les questions a laisse passer le defaut 58 pendant trois jours, et un
faux plus gentil que le reel ne prouve rien.

Aucune valeur reelle du bateau n apparait ici : les positions sont
volontairement fictives, la politique du depot etant que les valeurs de faits
n y sont pas consignees.
"""

import json
import math
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

DEPOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVEUR = os.path.join(DEPOT, "mcp", "servers", "racing.js")

INSTANT = "2026-09-07T14:36:24.298Z"
AS_OF = "2026-09-07T14:36:26Z"
FENETRE = 60

# valeurs fictives, choisies pour etre reconnaissables dans une sortie
LATITUDE = 41.1111111
LONGITUDE = -72.2222222
VITESSE_MS = 3.3333
CAP_RADIANS = 1.2345
CAP_DEGRES = math.degrees(CAP_RADIANS)  # 70.7316...

CHAMPS = {
    ("navigation.position", "lat"): "latitude",
    ("navigation.position", "lon"): "longitude",
    ("navigation.speedOverGround", "value"): "vitesse",
    ("navigation.courseOverGroundTrue", "value"): "cap",
}


def _extraire(flux, motif):
    """Extrait la valeur entre guillemets qui suit un motif dans la requete."""
    debut = flux.index(motif) + len(motif)
    reste = flux[debut:]
    premier = reste.index('"') + 1
    return reste[premier:reste.index('"', premier)]


class _Poignee(BaseHTTPRequestHandler):
    """Repond a la requete Flux selon la mesure et le champ demandes."""

    def log_message(self, *args):
        pass

    def do_POST(self):
        taille = int(self.headers.get("Content-Length", 0))
        flux = self.rfile.read(taille).decode("utf-8")
        self.server.requetes.append(flux)
        mesure = _extraire(flux, "_measurement ==")
        champ = _extraire(flux, "_field ==")
        nom = CHAMPS[(mesure, champ)]
        valeur = self.server.valeurs[nom]
        corps = (
            "#datatype,string,long,dateTime:RFC3339,double\r\n"
            "#group,false,false,false,false\r\n"
            "#default,_result,,,\r\n"
            ",result,table,_time,_value\r\n"
            ",,0,%s,%s\r\n\r\n" % (INSTANT, valeur)
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


def _demarrer(valeurs):
    """Demarre le faux InfluxDB sur un port libre et rend (serveur, port)."""
    serveur = HTTPServer(("127.0.0.1", 0), _Poignee)
    serveur.valeurs = valeurs
    serveur.requetes = []
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    return serveur, serveur.server_address[1]


def _instantane(cap, latitude=LATITUDE, longitude=LONGITUDE,
                vitesse=VITESSE_MS):
    """Interroge le vrai serveur racing.js et rend (charge, erreur, requetes).

    charge est le dictionnaire publie par get_historical_snapshot, ou None si
    le serveur a refuse ; erreur porte alors le message JSON-RPC.
    """
    if shutil.which("node") is None:
        raise RuntimeError(
            "node est absent : ce test ne peut pas etre saute en silence, "
            "c est le serveur lui-meme qu il verifie")
    valeurs = {"latitude": latitude, "longitude": longitude,
               "vitesse": vitesse, "cap": cap}
    serveur, port = _demarrer(valeurs)
    try:
        environnement = dict(os.environ)
        environnement.update({
            "INFLUX_URL": "http://127.0.0.1:%d" % port,
            "INFLUX_TOKEN": "jeton-de-test-sans-valeur-reelle-0123456789",
            "INFLUX_ORG": "midnightrider",
            "INFLUX_BUCKET": "midnight_rider",
        })
        demande = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "get_historical_snapshot",
                       "arguments": {"as_of_utc": AS_OF,
                                     "window_seconds": FENETRE}},
        })
        processus = subprocess.run(
            ["node", SERVEUR], input=demande + "\n", env=environnement,
            capture_output=True, text=True, timeout=60)
        lignes = [l for l in processus.stdout.splitlines() if l.strip()]
        assert lignes, ("le serveur n a rien repondu ; stderr = %s"
                        % processus.stderr[-800:])
        reponse = json.loads(lignes[-1])
        if "error" in reponse:
            return None, reponse["error"].get("message", ""), serveur.requetes
        enveloppe = reponse["result"]
        charge = json.loads(enveloppe["content"][0]["text"])
        return charge, None, serveur.requetes
    finally:
        serveur.shutdown()
        serveur.server_close()


def test_le_cap_est_converti_en_degres():
    """Le cap publie est la conversion du radian, pas le radian lui-meme."""
    charge, erreur, _ = _instantane(CAP_RADIANS)
    assert erreur is None, erreur
    publie = charge["facts"]["course_over_ground_degrees"]
    assert abs(publie - CAP_DEGRES) < 1e-9, (
        "attendu %.7f degres, publie %r" % (CAP_DEGRES, publie))
    assert abs(publie - CAP_RADIANS) > 1.0, (
        "le radian brut est encore publie sous une cle qui dit degres : %r"
        % publie)


def test_zero_radian_reste_zero_degre():
    """Cap nul : la conversion ne doit rien inventer."""
    charge, erreur, _ = _instantane(0)
    assert erreur is None, erreur
    assert charge["facts"]["course_over_ground_degrees"] == 0


def test_deux_pi_vaut_360_degres():
    """La borne haute du domaine radian est acceptee et vaut un tour."""
    charge, erreur, _ = _instantane(2 * math.pi)
    assert erreur is None, erreur
    publie = charge["facts"]["course_over_ground_degrees"]
    assert abs(publie - 360.0) < 1e-6, publie


def test_un_cap_hors_domaine_radian_fait_echouer_la_collecte():
    """Une valeur en degres arrivant a l entree doit echouer bruyamment.

    Si Signal K se mettait un jour a servir des degres, la convertir une
    seconde fois donnerait un cap absurde. Le serveur doit refuser, pas
    publier.
    """
    charge, erreur, _ = _instantane(197.7)
    assert charge is None, (
        "197.7 rad est hors domaine et a pourtant ete publie : %r" % (charge,))
    assert erreur, "aucun message d erreur"
    assert "incomplete" in erreur.lower() or "invalid" in erreur.lower(), erreur


def test_un_cap_negatif_est_refuse():
    """Le domaine est [0, 2*PI] : une valeur negative n est pas un cap."""
    charge, erreur, _ = _instantane(-0.5)
    assert charge is None, charge
    assert erreur


def test_les_unites_sont_declarees():
    """La reponse dit dans quelle unite chaque fait est publie."""
    charge, erreur, _ = _instantane(CAP_RADIANS)
    assert erreur is None, erreur
    unites = charge.get("units")
    assert isinstance(unites, dict), (
        "aucun bloc units : le contrat ne dit pas ses unites")
    assert unites == {
        "latitude": "degrees",
        "longitude": "degrees",
        "speed_over_ground_ms": "m_per_s",
        "course_over_ground_degrees": "degrees_true",
    }, unites
    assert set(charge["facts"]) == {
        "latitude", "longitude", "speed_over_ground_ms",
        "course_over_ground_degrees"}, (
        "le bloc units ne doit pas polluer l ensemble exact des quatre faits")


def test_les_autres_faits_ne_sont_pas_convertis():
    """Seul le cap change d unite : position en degres, vitesse en m/s."""
    charge, erreur, _ = _instantane(CAP_RADIANS)
    assert erreur is None, erreur
    faits = charge["facts"]
    assert faits["latitude"] == LATITUDE
    assert faits["longitude"] == LONGITUDE
    assert faits["speed_over_ground_ms"] == VITESSE_MS


def test_le_filtre_de_contexte_du_defaut_58_est_toujours_la():
    """Non-regression : les quatre requetes filtrent toujours self."""
    _, erreur, requetes = _instantane(CAP_RADIANS)
    assert erreur is None, erreur
    assert len(requetes) == 4, requetes
    for requete in requetes:
        assert 'r.self == "true"' in requete, requete
        assert requete.index('r.self == "true"') < requete.index("keep(columns"), (
            "le filtre doit preceder le keep(), sinon le tag self est detruit "
            "avant d avoir servi")
