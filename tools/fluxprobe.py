#!/usr/bin/env python3
"""Sonde Flux unique et testee du projet Midnight Rider.

Raison d'etre
-------------
Entre le 2026-09-16 et le 2026-09-17, quatre conclusions fausses ont ete
commitees dans un depot public parce que chaque script de diagnostic
reimprovisait sa propre sonde InfluxDB. Les defauts 55, 59 et 60 ont la
meme origine : une reponse partielle ou absente lue comme une reponse
complete.

Ce module est desormais la seule sonde autorisee. Il impose trois
disciplines, chacune verrouillee par un test de non-regression :

1. Quatre etats explicites et mutuellement exclusifs : DATA, EMPTY,
   TIMEOUT, ERROR. Une erreur n'est jamais silencieuse et porte toujours
   un message non vide (defaut 59 : 11 sondes sur 12 ont renvoye une
   erreur dont le message etait capture puis jamais affiche).

2. Aucune lecture de `rows[0]`. Une reponse Flux non groupee contient une
   ligne PAR SERIE, dans un ordre non garanti. `single_row()` refuse de
   choisir, `latest_row()` trie explicitement par horodatage, et
   `require_single_series()` permet d'exiger une reponse non ambigue
   (defaut 60).

3. Aucun taux calcule sur les seules sondes reussies. `Tally.rate()` leve
   une exception tant qu'une tentative a echoue : le denominateur est le
   nombre de TENTATIVES, jamais le nombre de succes (defaut 59).

Le module n'utilise que la bibliotheque standard et ne journalise jamais
de jeton : tout message sortant passe par `scrub()`.

Pourquoi ce module ne reutilise pas tools/influx_powerbi_export/
----------------------------------------------------------------
La question a ete posee avant d'ecrire une ligne. Trois raisons, dans
l'ordre d'importance :

1. Chemin d'acces different, et c'est voulu. `InfluxClient` interroge
   InfluxDB par la CLI interne au conteneur Docker, sans jeton. MediaMan,
   lui, passe par HTTP avec le jeton de .env, parce que c'est ce que fait
   `mcp/servers/racing.js`. Une sonde de diagnostic doit emprunter le
   MEME chemin que le code qu'elle mesure, sinon elle mesure autre chose.

2. `AnnotatedCSVParser.parse_stream()` abandonne silencieusement toute
   ligne dont la largeur differe de l'en-tete (`if len(row) == len(headers)`
   sans branche `else`). C'est precisement le motif qu'on elimine ici.
   Ce point est signale a l'equipe de l'export ; ce module n'y touche pas.

3. Le paquet `tools.influx_powerbi_export` declenche des appels Docker a
   l'import selon les chemins ; le coupler a un outil de diagnostic
   MediaMan creerait une dependance non desiree.

En revanche `is_ais_context()` reprend DELIBEREMENT la regle de
`Classifier.classify()` du meme paquet, pour que les deux projets ne
divergent pas sur la definition d'une cible AIS.
"""

from __future__ import annotations

import csv
import hashlib
import math
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, Optional, Sequence, Tuple

__all__ = [
    "STATE_DATA", "STATE_EMPTY", "STATE_TIMEOUT", "STATE_ERROR", "STATES",
    "FluxError", "ConfigError", "AmbiguousResult", "EmptyResult",
    "MalformedRow", "IncompleteMeasurement",
    "FluxResult", "FluxProbe", "Tally",
    "parse_annotated_csv", "parse_rfc3339", "as_float", "scrub", "mask_number",
    "is_ais_context",
]

STATE_DATA = "DATA"
STATE_EMPTY = "EMPTY"
STATE_TIMEOUT = "TIMEOUT"
STATE_ERROR = "ERROR"
STATES = (STATE_DATA, STATE_EMPTY, STATE_TIMEOUT, STATE_ERROR)

# Colonnes techniques de l'annotated CSV : elles n'identifient pas une serie
# au sens metier, mais `result` et `table` la delimitent.
_TECHNICAL_COLUMNS = ("result", "table", "_start", "_stop", "_time", "_value")

# En dessous de cette longueur, une valeur n'est pas masquee : masquer une
# chaine courte revelerait sa position sans proteger grand chose.
_MIN_SECRET_LENGTH = 12


class FluxError(Exception):
    """Erreur de base de la sonde Flux."""


class ConfigError(FluxError):
    """Configuration absente ou incomplete. Ne contient jamais de valeur."""


class AmbiguousResult(FluxError):
    """La reponse contient plusieurs lignes ou plusieurs series.

    Levee plutot que de choisir arbitrairement : c'est exactement le geste
    (`rows[0]`) qui a produit le defaut 60.
    """


class EmptyResult(FluxError):
    """La reponse ne contient aucune ligne alors qu'une etait attendue."""


class MalformedRow(FluxError):
    """Une ligne ne porte pas la colonne attendue, ou pas sous forme lisible."""


class IncompleteMeasurement(FluxError):
    """Un taux a ete demande alors que des tentatives ont echoue."""


def scrub(text: str, secrets: Iterable[str]) -> str:
    """Remplace toute occurrence d'un secret par un marqueur.

    Les chaines de moins de `_MIN_SECRET_LENGTH` caracteres sont ignorees.
    """
    out = text or ""
    for secret in secrets:
        if secret and len(secret) >= _MIN_SECRET_LENGTH:
            out = out.replace(secret, "[REDACTED]")
    return out


def mask_number(text: str, decimals: int = 1) -> str:
    """Tronque un nombre decimal pour un depot public.

    Une latitude a trois decimales localise un bateau a une centaine de
    metres. Les journaux du depot n'en ont pas besoin.
    """
    raw = (text or "").strip()
    if "." not in raw:
        return raw
    head, _, tail = raw.partition(".")
    kept = tail[:decimals]
    if len(tail) <= decimals:
        return raw
    return head + "." + kept + "<masque>"


def is_ais_context(context: Optional[str]) -> bool:
    """Vrai si ce contexte Signal K designe une cible AIS ou une balise.

    Reprend mot pour mot la regle de `Classifier.classify()` dans
    tools/influx_powerbi_export/classifier.py : un contexte est AIS s'il
    contient a la fois "mmsi" et "urn". Cela couvre les cibles navires
    (`vessels.urn:mrn:imo:mmsi:...`) et les balises AtoN
    (`atons.urn:mrn:imo:mmsi:...`).

    Attention a la portee : ce test dit "AIS ou pas", il ne dit PAS
    "notre bateau ou pas". Un contexte non-AIS n'est pas necessairement le
    Midnight Rider. Pour designer le bateau, comparer a son UUID exact.
    """
    lowered = (context or "").lower()
    return "mmsi" in lowered and "urn" in lowered


def parse_rfc3339(text: Optional[str]) -> Optional[datetime]:
    """Convertit un horodatage RFC3339 InfluxDB en datetime conscient du fuseau.

    Tolere la precision nanoseconde renvoyee par InfluxDB v2, que
    `datetime.fromisoformat` refuse (il n'accepte que 0, 3 ou 6 chiffres).
    Renvoie None si la chaine n'est pas exploitable, jamais une exception.
    """
    if not text:
        return None
    raw = text.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    if "." in raw:
        head, _, tail = raw.partition(".")
        index = 0
        while index < len(tail) and tail[index].isdigit():
            index += 1
        digits = (tail[:index] + "000000")[:6]
        raw = head + "." + digits + tail[index:]
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def as_float(text: Optional[str]) -> Optional[float]:
    """Convertit une valeur InfluxDB en float fini, ou None.

    InfluxDB renvoie toujours `_value` sous forme de chaine. Un NaN ou un
    infini n'est pas une mesure : il est rejete explicitement plutot que
    propage.
    """
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return value


def parse_annotated_csv(body: str) -> Tuple[Dict[str, str], ...]:
    """Decoupe un annotated CSV InfluxDB en lignes nommees.

    Gere : les lignes d'annotation `#datatype` / `#group` / `#default`, les
    fins de ligne CRLF, la premiere colonne au nom vide, les blocs multiples
    separes par une ligne blanche, et les valeurs contenant une virgule.

    Renvoie TOUTES les lignes, dans l'ordre du document. L'ordre du document
    n'est PAS un ordre chronologique : utiliser `FluxResult.latest_row()`.
    """
    rows = []
    header: Optional[Sequence[str]] = None
    normalised = (body or "").replace("\r\n", "\n").replace("\r", "\n")
    for line in normalised.split("\n"):
        if not line.strip():
            header = None
            continue
        if line.startswith("#"):
            header = None
            continue
        cells = next(csv.reader([line]))
        if header is None:
            header = cells
            continue
        row = {}
        for name, value in zip(header, cells):
            if name:
                row[name] = value
        rows.append(row)
    return tuple(rows)


@dataclass(frozen=True)
class FluxResult:
    """Resultat d'une requete Flux, dans l'un des quatre etats.

    `rows` contient TOUTES les lignes renvoyees. Aucun accesseur ne prend
    silencieusement la premiere.
    """

    state: str
    rows: Tuple[Dict[str, str], ...] = ()
    detail: str = ""
    elapsed_s: float = 0.0
    query: str = ""

    def __post_init__(self) -> None:
        if self.state not in STATES:
            raise FluxError("etat inconnu : %r" % (self.state,))
        if self.state in (STATE_TIMEOUT, STATE_ERROR) and not self.detail:
            raise FluxError("un etat %s doit porter un message" % self.state)

    @property
    def ok(self) -> bool:
        """Vrai uniquement si la requete a rendu au moins une ligne."""
        return self.state == STATE_DATA

    @property
    def failed(self) -> bool:
        """Vrai si la requete n'a pas abouti. EMPTY n'est pas un echec."""
        return self.state in (STATE_TIMEOUT, STATE_ERROR)

    def series_keys(self) -> Tuple[Tuple[str, str], ...]:
        """Couples (result, table) distincts presents dans la reponse.

        Dans l'annotated CSV, `table` numerote les series. Deux series
        signifient que `last()` a renvoye deux points, un par serie.
        """
        seen = []
        for row in self.rows:
            key = (row.get("result", ""), row.get("table", ""))
            if key not in seen:
                seen.append(key)
        return tuple(seen)

    @property
    def series_count(self) -> int:
        """Nombre de series distinctes. 0 si la reponse est vide."""
        return len(self.series_keys())

    def require_state(self, expected: str) -> "FluxResult":
        """Impose un etat, sinon leve avec le message d'erreur reel."""
        if self.state != expected:
            raise FluxError(
                "etat %s attendu, obtenu %s : %s"
                % (expected, self.state, self.detail or "(pas de message)"))
        return self

    def require_single_series(self) -> "FluxResult":
        """Impose une reponse non ambigue : exactement une serie.

        A utiliser des qu'on s'apprete a parler DU point, au singulier.
        """
        count = self.series_count
        if count != 1:
            raise AmbiguousResult(
                "%d serie(s) dans la reponse : la requete doit etre groupee "
                "(group()) ou filtree davantage avant de parler d'une valeur "
                "unique. Series : %s" % (count, list(self.series_keys())[:5]))
        return self

    def single_row(self) -> Dict[str, str]:
        """Renvoie l'unique ligne, ou leve. Ne choisit jamais a la place."""
        if not self.rows:
            raise EmptyResult("aucune ligne : %s" % (self.detail or self.state))
        if len(self.rows) != 1:
            raise AmbiguousResult(
                "%d lignes et %d serie(s) : refus de prendre la premiere "
                "(defaut 60). Grouper la requete ou utiliser latest_row()."
                % (len(self.rows), self.series_count))
        return self.rows[0]

    def latest_row(self, time_column: str = "_time") -> Dict[str, str]:
        """Renvoie la ligne au `_time` le plus recent, par tri explicite.

        L'ordre du document n'est pas chronologique quand plusieurs series
        sont presentes. C'est precisement ce qui a produit des ecarts de
        200 secondes annonces comme des ecarts de 148 millisecondes.
        """
        if not self.rows:
            raise EmptyResult("aucune ligne : %s" % (self.detail or self.state))
        dated = []
        for row in self.rows:
            stamp = parse_rfc3339(row.get(time_column))
            if stamp is None:
                raise MalformedRow(
                    "ligne sans colonne %s exploitable : colonnes presentes %s"
                    % (time_column, sorted(row.keys())))
            dated.append((stamp, row))
        dated.sort(key=lambda pair: pair[0])
        return dated[-1][1]

    def latest_time(self, time_column: str = "_time") -> datetime:
        """Horodatage le plus recent de la reponse."""
        stamp = parse_rfc3339(self.latest_row(time_column).get(time_column))
        if stamp is None:
            raise MalformedRow("horodatage illisible")
        return stamp


class FluxProbe:
    """Client InfluxDB v2 minimal, bornee dans le temps et sans surprise.

    Chaque appel renvoie un `FluxResult`. Aucune exception reseau ne
    remonte : elle est traduite en etat TIMEOUT ou ERROR avec un message.
    """

    def __init__(self, url: str, org: str, token: str, bucket: str,
                 default_timeout: float = 20.0) -> None:
        self.url = (url or "").rstrip("/")
        self.org = org or ""
        self.bucket = bucket or ""
        self._token = token or ""
        self.default_timeout = float(default_timeout)

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None,
                 default_timeout: float = 20.0) -> "FluxProbe":
        """Construit la sonde depuis INFLUX_URL / TOKEN / ORG / BUCKET.

        En cas d'absence, le message nomme les variables manquantes et
        n'affiche AUCUNE valeur.
        """
        source = os.environ if env is None else env
        names = ("INFLUX_URL", "INFLUX_TOKEN", "INFLUX_ORG", "INFLUX_BUCKET")
        missing = [name for name in names if not (source.get(name) or "").strip()]
        if missing:
            raise ConfigError(
                "variable(s) d'environnement absente(s) : %s" % ", ".join(missing))
        return cls(url=source["INFLUX_URL"].strip(),
                   org=source["INFLUX_ORG"].strip(),
                   token=source["INFLUX_TOKEN"].strip(),
                   bucket=source["INFLUX_BUCKET"].strip(),
                   default_timeout=default_timeout)

    def token_fingerprint(self) -> str:
        """Empreinte courte du jeton, pour tracer sans divulguer."""
        if len(self._token) < 30:
            return "(trop court pour etre empreinte sans risque)"
        return hashlib.sha256(self._token.encode("utf-8")).hexdigest()[:16]

    def _send(self, flux: str, timeout: float) -> str:
        """Seam de test : envoie la requete et renvoie le corps brut."""
        request = urllib.request.Request(
            "%s/api/v2/query?org=%s" % (self.url, urllib.parse.quote(self.org)),
            method="POST",
            headers={"Authorization": "Token " + self._token,
                     "Content-Type": "application/vnd.flux",
                     "Accept": "application/csv"})
        with urllib.request.urlopen(request, data=flux.encode("utf-8"),
                                    timeout=timeout) as response:
            return response.read().decode("utf-8", "replace")

    def query(self, flux: str, timeout: Optional[float] = None) -> FluxResult:
        """Execute une requete Flux et renvoie l'un des quatre etats."""
        delay = self.default_timeout if timeout is None else float(timeout)
        started = time.time()
        safe_query = scrub(flux, [self._token])
        try:
            body = self._send(flux, delay)
        except (socket.timeout, TimeoutError):
            return FluxResult(STATE_TIMEOUT, (),
                              "delai depasse apres %.1f s" % delay,
                              time.time() - started, safe_query)
        except urllib.error.HTTPError as error:
            try:
                payload = error.read().decode("utf-8", "replace")[:400]
            except Exception:  # noqa: BLE001 - le corps peut etre illisible
                payload = "(corps de reponse illisible)"
            return FluxResult(STATE_ERROR, (),
                              scrub("HTTP %s : %s" % (error.code, payload),
                                    [self._token]),
                              time.time() - started, safe_query)
        except urllib.error.URLError as error:
            reason = getattr(error, "reason", None)
            if isinstance(reason, (socket.timeout, TimeoutError)):
                return FluxResult(STATE_TIMEOUT, (),
                                  "delai depasse apres %.1f s" % delay,
                                  time.time() - started, safe_query)
            return FluxResult(STATE_ERROR, (),
                              scrub("URLError : %s" % (reason,), [self._token]),
                              time.time() - started, safe_query)
        except Exception as error:  # noqa: BLE001 - aucune erreur silencieuse
            return FluxResult(STATE_ERROR, (),
                              scrub("%s : %s" % (type(error).__name__, error),
                                    [self._token]),
                              time.time() - started, safe_query)
        rows = parse_annotated_csv(body)
        state = STATE_DATA if rows else STATE_EMPTY
        return FluxResult(state, rows, "", time.time() - started, safe_query)


@dataclass
class Tally:
    """Compteur de campagne de mesure a denominateur honnete.

    `rate()` refuse de produire un taux tant qu'une tentative a echoue.
    C'est la barriere qui manquait quand 11 sondes sur 12 ont echoue et
    que le rapport a affiche un taux de 1 sur 1.
    """

    label: str
    counts: Dict[str, int] = field(default_factory=lambda: {s: 0 for s in STATES})
    failures_detail: list = field(default_factory=list)

    def record(self, result: FluxResult) -> FluxResult:
        """Enregistre une tentative, quel qu'en soit le resultat."""
        self.counts[result.state] = self.counts.get(result.state, 0) + 1
        if result.failed:
            self.failures_detail.append("%s: %s" % (result.state, result.detail))
        return result

    @property
    def attempts(self) -> int:
        """Nombre total de tentatives. C'est le seul denominateur legitime."""
        return sum(self.counts.values())

    @property
    def failures(self) -> int:
        """Tentatives TIMEOUT ou ERROR. EMPTY n'est pas un echec."""
        return self.counts.get(STATE_TIMEOUT, 0) + self.counts.get(STATE_ERROR, 0)

    def rate(self, numerator: int, allow_partial: bool = False) -> str:
        """Renvoie 'n/tentatives', ou leve si des tentatives ont echoue."""
        if self.failures and not allow_partial:
            raise IncompleteMeasurement(
                "%s : %d tentative(s) dont %d en echec non explique. Aucun "
                "taux ne peut etre calcule sur les seules reussites. "
                "Echecs : %s" % (self.label, self.attempts, self.failures,
                                 " | ".join(self.failures_detail[:3])))
        return "%d/%d" % (numerator, self.attempts)

    def summary(self) -> str:
        """Ligne de synthese montrant TOUJOURS les quatre etats."""
        return ("%s : %d tentative(s) = %d DATA, %d EMPTY, %d TIMEOUT, %d ERROR"
                % (self.label, self.attempts, self.counts.get(STATE_DATA, 0),
                   self.counts.get(STATE_EMPTY, 0),
                   self.counts.get(STATE_TIMEOUT, 0),
                   self.counts.get(STATE_ERROR, 0)))

    def as_dict(self) -> Dict[str, object]:
        """Forme serialisable pour logs/latest.json."""
        return {"label": self.label, "attempts": self.attempts,
                "counts": dict(self.counts), "failures": self.failures}
