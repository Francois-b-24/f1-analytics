"""Tests du chemin de chargement de session — 100 % hors ligne.

Couvre les modes de défaillance observés en production, où l'API F1 publie des
données partielles : `load()` qui échoue et `sess.laps` qui lève
`DataNotLoadedError`. Ces accès n'étaient pas protégés et remontaient jusqu'à
l'interface sous forme d'erreur brute.
"""
import pandas as pd
import pytest

import src.data as data_module


class _FakeLaps(pd.DataFrame):
    """DataFrame de tours minimal (FastF1 en renvoie une sous-classe)."""

    @property
    def _constructor(self):
        return _FakeLaps

    def pick_drivers(self, drv):  # pragma: no cover - non utilisé ici
        return self[self["Driver"] == drv]


def _laps_valides() -> _FakeLaps:
    return _FakeLaps({
        "Driver": ["VER", "HAM"],
        "LapNumber": [1, 1],
        "LapTime": [pd.Timedelta(seconds=90), pd.Timedelta(seconds=91)],
    })


class _SessionOK:
    """Session dont le chargement complet réussit."""

    name = "Race"

    def __init__(self):
        self.appels = []

    def load(self, **kwargs):
        self.appels.append(kwargs)

    @property
    def laps(self):
        return _laps_valides()


class _SessionSansTelemetrie(_SessionOK):
    """`load()` complet échoue, le repli sans télémétrie réussit.

    Reproduit le cas d'une session dont la télémétrie n'est pas encore publiée.
    """

    def load(self, **kwargs):
        self.appels.append(kwargs)
        if not kwargs:  # appel complet
            raise RuntimeError("telemetry unavailable")


class _SessionSansTours(_SessionOK):
    """`sess.laps` lève, comme FastF1 quand les tours ne sont pas chargés."""

    @property
    def laps(self):
        raise RuntimeError("DataNotLoadedError: data has not been loaded yet")


@pytest.fixture
def sans_extraction(monkeypatch):
    """Neutralise l'extraction télémétrie, hors sujet pour ces tests."""
    monkeypatch.setattr(data_module, "_extract_best_lap_tel", lambda sess, codes: {})


def test_build_session_repli_sans_telemetrie(monkeypatch, sans_extraction):
    """Si le chargement complet échoue, on retente sans télémétrie."""
    sess = _SessionSansTelemetrie()
    monkeypatch.setattr(data_module.fastf1, "get_session", lambda *a, **k: sess)

    retour, tel, best = data_module._build_session(2026, "Belgian Grand Prix", "R")

    assert retour is sess
    # Un appel complet, puis un repli explicite sans télémétrie
    assert sess.appels[0] == {}
    assert sess.appels[1] == {"telemetry": False, "weather": False, "messages": False}
    assert tel == {}


def test_build_session_tours_indisponibles(monkeypatch, sans_extraction):
    """Un accès aux tours impossible donne une erreur explicite, pas brute."""
    monkeypatch.setattr(
        data_module.fastf1, "get_session", lambda *a, **k: _SessionSansTours()
    )

    with pytest.raises(RuntimeError, match="Données de tours indisponibles"):
        data_module._build_session(2026, "Belgian Grand Prix", "R")


def test_build_session_nominal(monkeypatch, sans_extraction):
    """Cas nominal : un seul appel à load(), les pilotes sont extraits."""
    sess = _SessionOK()
    monkeypatch.setattr(data_module.fastf1, "get_session", lambda *a, **k: sess)

    retour, _, _ = data_module._build_session(2024, "Australian Grand Prix", "R")

    assert retour is sess
    assert sess.appels == [{}]  # pas de repli déclenché inutilement
