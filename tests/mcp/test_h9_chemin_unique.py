#!/usr/bin/env python3
"""H9 - un seul chemin de collecte, deux portes d entree.

Jusqu au 2026-09-18 il y avait deux chemins. L historique interrogeait
InfluxDB en une requete par fait, filtrait sur self, bornait la derive entre
les quatre horodatages et convertissait le cap des radians vers les degres.
Le temps reel demandait position, vitesse et cap a trois outils separes que
mcp/servers/racing.js n a jamais declares : il ne pouvait donc rien collecter
du tout, et s il avait ete complete tel quel il aurait rouvert le defaut 58
(pas de filtre self) et le defaut 63 (pas de conversion), sur le chemin
destine a la course. C etait le defaut 65.

Decision de Denis le 2026-09-18 : un seul chemin, dont l horizon temporel est
un parametre. Consulter en direct, c est demander l intervalle qui se termine
maintenant ; rejouer le passe, c est demander un intervalle plus ancien.

Ces tests verrouillent la convergence elle-meme, pas seulement son resultat :
  - il n existe qu un seul constructeur de requete Flux dans le serveur ;
  - les deux portes emettent des requetes Flux identiques ;
  - les deux portes rendent des faits et des unites identiques ;
  - les acquis des defauts 58 et 63 valent par la nouvelle porte aussi ;
  - les bornes aberrantes sont refusees ;
  - les trois outils morts ne peuvent pas reapparaitre.

Le faux InfluxDB LIT la requete Flux et repond selon la mesure et le champ
demandes : un faux qui repond la meme chose a toutes les questions est
exactement ce qui a laisse vivre le defaut 58.

Aucune valeur reelle du bateau n apparait ici.
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
COLLECTEUR = os.path.join(DEPOT, "mediaman", "mcp_collector.py")

INSTANT = "2026-09-07T14:36:24.298Z"
DEBUT = "2026-09-07T14:35:26Z"
FIN = "2026-09-07T14:36:26Z"
FENETRE = 60

# Le moteur normalise ses deux bornes avant de construire la requete. Sans
# cette normalisation les deux portes produiraient, pour le meme intervalle,
# des requetes Flux textuellement differentes : la porte historique calcule sa
# borne basse avec toISOString() et obtient .000Z, la porte de plage recoit la
# chaine que l appelant a ecrite. Meme instant, autre chaine.
DEBUT_CANONIQUE = "2026-09-07T14:35:26.000Z"
FIN_CANONIQUE = "2026-09-07T14:36:26.000Z"

LATITUDE = 41.1111111
LONGITUDE = -72.2222222
VITESSE_MS = 3.3333
CAP_RADIANS = 1.2345
CAP_DEGRES = math.degrees(CAP_RADIANS)

CHAMPS = {
    ("navigation.position", "lat"): "latitude",
    ("navigation.position", "lon"): "longitude",
    ("navigation.speedOverGround", "value"): "vitesse",
    ("navigation.courseOverGroundTrue", "value"): "cap",
}

VALEURS = {"latitude": LATITUDE, "longitude": LONGITUDE,
           "vitesse": VITESSE_MS, "cap": CAP_RADIANS}


def _extraire(flux, motif):
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
        valeur = self.server.valeurs[CHAMPS[(mesure, champ)]]
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
    serveur = HTTPServer(("127.0.0.1", 0), _Poignee)
    serveur.valeurs = valeurs
    serveur.requetes = []
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    return serveur, serveur.server_address[1]


def _appeler(nom_outil, arguments, valeurs=None):
    """Interroge le vrai racing.js et rend (charge, erreur, requetes Flux)."""
    if shutil.which("node") is None:
        raise RuntimeError(
            "node est absent : ce test ne peut pas etre saute en silence, "
            "c est le serveur lui-meme qu il verifie")
    serveur, port = _demarrer(dict(valeurs or VALEURS))
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
            "params": {"name": nom_outil, "arguments": arguments},
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
        charge = json.loads(reponse["result"]["content"][0]["text"])
        return charge, None, serveur.requetes
    finally:
        serveur.shutdown()
        serveur.server_close()


def _par_plage(debut=DEBUT, fin=FIN, valeurs=None):
    return _appeler("get_snapshot",
                    {"start_utc": debut, "end_utc": fin}, valeurs)


def _par_instant(fin=FIN, fenetre=FENETRE, valeurs=None):
    return _appeler("get_historical_snapshot",
                    {"as_of_utc": fin, "window_seconds": fenetre}, valeurs)


def _outils_declares():
    if shutil.which("node") is None:
        raise RuntimeError("node est absent")
    demande = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    processus = subprocess.run(
        ["node", SERVEUR], input=demande + "\n",
        capture_output=True, text=True, timeout=60)
    lignes = [l for l in processus.stdout.splitlines() if l.strip()]
    assert lignes, "le serveur n a rien repondu a tools/list"
    return [o["name"] for o in json.loads(lignes[-1])["result"]["tools"]]


# ---------------------------------------------------------------- structure

def test_le_moteur_flux_est_unique():
    """Un seul endroit du serveur construit une requete Flux.

    C est l assertion centrale de H9. Tant qu elle tient, les deux portes ne
    peuvent pas diverger : il n y a materiellement qu un moteur. Si quelqu un
    ecrit une seconde requete, pour une bonne raison ou non, ce test rougit
    et la decision redevient explicite.
    """
    texte = open(SERVEUR, encoding="utf-8").read()
    ouvertures = texte.count("from" + "(bucket:")
    assert ouvertures == 1, (
        "%d constructeur(s) de requete Flux dans racing.js ; H9 en exige "
        "exactement un, sinon les deux portes peuvent diverger" % ouvertures)


def test_les_deux_portes_sont_declarees():
    """Les deux outils existent reellement, et le serveur le dit."""
    noms = _outils_declares()
    assert "get_historical_snapshot" in noms, noms
    assert "get_snapshot" in noms, noms


def test_les_trois_outils_morts_ne_reapparaissent_pas():
    """Le collecteur n adresse plus les trois outils jamais declares.

    Ce sont les noms cites litteralement qui sont interdits, pas les noms
    cites en commentaire : l explication historique du defaut 65 doit pouvoir
    rester dans le fichier.
    """
    texte = open(COLLECTEUR, encoding="utf-8").read()
    interdits = ["%sracing.get_%s%s" % (g, n, g)
                 for n in ("position", "sog", "cog") for g in ("'", '"')]
    presents = {m: texte.count(m) for m in interdits if m in texte}
    assert not presents, (
        "le chemin mort du defaut 65 est de retour : %s" % presents)


# --------------------------------------------------------------- convergence

def test_les_deux_portes_emettent_la_meme_requete_flux():
    """Meme intervalle demande, requetes Flux identiques au caractere pres."""
    _, erreur_plage, requetes_plage = _par_plage()
    assert erreur_plage is None, erreur_plage
    _, erreur_instant, requetes_instant = _par_instant()
    assert erreur_instant is None, erreur_instant

    assert len(requetes_plage) == 4, len(requetes_plage)
    assert requetes_plage == requetes_instant, (
        "les deux portes n interrogent pas InfluxDB de la meme maniere")


def test_les_deux_portes_rendent_les_memes_faits():
    """Faits et unites identiques : la convergence est verifiee, pas promise."""
    par_plage, erreur_plage, _ = _par_plage()
    assert erreur_plage is None, erreur_plage
    par_instant, erreur_instant, _ = _par_instant()
    assert erreur_instant is None, erreur_instant

    assert par_plage["facts"] == par_instant["facts"]
    assert par_plage["units"] == par_instant["units"]
    assert par_plage["source_timestamp"] == par_instant["source_timestamp"]
    assert par_plage["fact_timestamps"] == par_instant["fact_timestamps"]
    assert par_plage["bounded_skew_ms"] == par_instant["bounded_skew_ms"]


def test_la_plage_est_rendue_dans_la_reponse():
    """Un consommateur ne doit jamais avoir a deviner l intervalle recu."""
    charge, erreur, _ = _par_plage()
    assert erreur is None, erreur
    assert charge["interval"]["start_utc"] == DEBUT_CANONIQUE
    assert charge["interval"]["end_utc"] == FIN_CANONIQUE
    assert charge["interval"]["duration_seconds"] == FENETRE


def test_les_bornes_sont_normalisees_avant_la_requete():
    """Deux ecritures du meme instant donnent la meme requete.

    C est la condition technique de la convergence textuelle : sans elle les
    deux portes seraient equivalentes sans etre identiques, et le test de
    convergence ne pourrait comparer que des resultats, jamais des requetes.
    """
    _, erreur, requetes = _par_plage(debut=DEBUT_CANONIQUE, fin=FIN_CANONIQUE)
    assert erreur is None, erreur
    _, erreur_brut, requetes_brut = _par_plage(debut=DEBUT, fin=FIN)
    assert erreur_brut is None, erreur_brut
    assert requetes == requetes_brut


# ------------------------------------------- acquis 58 et 63 par la porte neuve

def test_le_filtre_de_contexte_du_defaut_58_vaut_pour_la_porte_de_plage():
    """Le filtre self est present, et toujours AVANT le keep()."""
    _, erreur, requetes = _par_plage()
    assert erreur is None, erreur
    assert len(requetes) == 4
    for flux in requetes:
        assert 'r.self == "true"' in flux, (
            "requete sans filtre de contexte : le defaut 58 est de retour")
        assert flux.index('r.self == "true"') < flux.index("keep(columns:"), (
            "le filtre self est passe SOUS le keep(), qui detruit le tag : "
            "il ne filtre donc plus rien")


def test_le_cap_est_en_degres_par_la_porte_de_plage():
    """Le defaut 63 ne revient pas par la nouvelle entree."""
    charge, erreur, _ = _par_plage()
    assert erreur is None, erreur
    publie = charge["facts"]["course_over_ground_degrees"]
    assert abs(publie - CAP_DEGRES) < 1e-9, (
        "attendu %.7f degres, publie %r" % (CAP_DEGRES, publie))
    assert charge["units"]["course_over_ground_degrees"] == "degrees_true"


# ------------------------------------------------------------- bornes refusees

def test_une_plage_inversee_est_refusee():
    """Une fin anterieure au debut n est pas un intervalle."""
    charge, erreur, _ = _par_plage(debut=FIN, fin=DEBUT)
    assert charge is None
    assert "strictly after" in erreur, erreur


def test_une_plage_nulle_est_refusee():
    """Un intervalle de duree nulle non plus."""
    charge, erreur, _ = _par_plage(debut=FIN, fin=FIN)
    assert charge is None
    assert "strictly after" in erreur, erreur


def test_une_plage_trop_longue_est_refusee():
    """Au-dela d une heure, la requete n est plus bornee de facon sure."""
    charge, erreur, _ = _par_plage(debut="2026-09-07T12:00:00Z",
                                   fin="2026-09-07T14:00:01Z")
    assert charge is None
    assert "3600" in erreur, erreur


def test_une_borne_sans_suffixe_z_est_refusee():
    """Pas de fuseau implicite : l heure locale a deja coute assez cher."""
    charge, erreur, _ = _par_plage(fin="2026-09-07T14:36:26+00:00")
    assert charge is None
    assert "Z" in erreur, erreur
