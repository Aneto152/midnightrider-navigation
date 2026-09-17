"""
Empeche la reintroduction du defaut 49.

CE QUE CE FICHIER GARDE
-----------------------
Le 2026-09-17, tests/mediaman/test_historical_request.py fabriquait un instant
futur avec :

    future_dt.replace(second=future_dt.second + 10)

`datetime.replace()` remplace un CHAMP, il ne fait pas d arithmetique. Si la
seconde courante valait 50 ou plus, le champ depassait 59 et l appel levait
ValueError. Le test echouait donc 10 secondes sur 60 - 16,7 % des executions -
depuis sa creation. Il est passe a 00:45Z et a echoue a 01:32Z avec exactement
le meme code, ce qui a longtemps fait croire a une suite entierement verte.

La lecon n est pas de corriger l occurrence mais d interdire le motif : ce
fichier echoue si quiconque le reintroduit, dans n importe quel test.

Pour ajouter ou retirer une duree a un datetime, utiliser timedelta.
"""

import re
from pathlib import Path

import pytest

# Les mois et les annees ne sont pas des durees fixes : les ajouter par
# timedelta n a pas de sens, donc ils ne figurent pas ici.
FRAGILE_FIELDS = ("second", "minute", "hour", "day")

TESTS_ROOT = Path(__file__).resolve().parent.parent


def _fragile_pattern(field: str) -> re.Pattern:
    """VAR.replace(champ=VAR.champ + N) - le motif exact du defaut 49."""
    return re.compile(
        rf"(?P<var>\w+)\.replace\(\s*{field}\s*=\s*(?P=var)\.{field}\s*\+\s*\d+\s*\)"
    )


def _python_test_files():
    return sorted(
        p for p in TESTS_ROOT.rglob("*.py")
        if p.name != Path(__file__).name
    )


@pytest.mark.parametrize("field", FRAGILE_FIELDS)
def test_no_field_arithmetic_through_replace(field):
    """Aucun test du depot ne doit faire d arithmetique via .replace()."""
    pattern = _fragile_pattern(field)
    offenders = []
    for path in _python_test_files():
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for match in pattern.finditer(text):
            line = text[: match.start()].count("\n") + 1
            offenders.append(f"{path.relative_to(TESTS_ROOT)}:{line} -> {match.group(0)}")
    assert not offenders, (
        f"arithmetique fragile sur le champ '{field}' (defaut 49). "
        f"Utiliser timedelta({field}s=N) a la place de .replace({field}=...+N). "
        f"Occurrences : {offenders}"
    )


def test_the_guard_actually_detects_the_original_defect():
    """
    Un garde qui ne detecte rien serait un test vert sans objet. On verifie
    donc qu il reconnait bien l expression exacte qui a cause le defaut 49.
    """
    culprit = "future_dt = future_dt.replace(second=future_dt.second + 10)"
    assert _fragile_pattern("second").search(culprit) is not None


def test_the_guard_does_not_flag_legitimate_replace_calls():
    """
    Remettre un champ a une valeur fixe est parfaitement legitime et ne doit
    pas etre signale - par exemple pour tronquer a la minute.
    """
    legitimate = [
        "d.replace(second=0)",
        "d.replace(microsecond=0)",
        "d.replace(hour=12, minute=0, second=0)",
        "d.replace(tzinfo=timezone.utc)",
        "other.replace(second=d.second + 10)",  # variables differentes
    ]
    pattern = _fragile_pattern("second")
    for expression in legitimate:
        assert pattern.search(expression) is None, expression


def test_timedelta_crosses_the_minute_boundary():
    """La correction elle-meme : sur toute la minute, aucune exception."""
    from datetime import datetime, timedelta, timezone

    for second in range(60):
        base = datetime(2026, 9, 17, 1, 32, second, tzinfo=timezone.utc)
        shifted = base + timedelta(seconds=10)
        assert (shifted - base) == timedelta(seconds=10)
        assert shifted > base


def test_the_original_expression_really_did_fail_in_that_window():
    """
    Documente le mecanisme par execution, pour que personne n ait a me croire
    sur parole : les secondes 50 a 59 levaient bien ValueError.
    """
    from datetime import datetime, timezone

    failures = 0
    for second in range(60):
        base = datetime(2026, 9, 17, 1, 32, second, tzinfo=timezone.utc)
        try:
            base.replace(second=base.second + 10)
        except ValueError:
            failures += 1
    assert failures == 10
