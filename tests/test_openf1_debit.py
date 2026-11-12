"""Limitation du débit vers OpenF1 — entièrement hors ligne.

Contexte : l'API plafonne le débit (mesuré en novembre 2026 : HTTP 429 après
6 requêtes en 0,72 s). Sans espacement, les threads parallèles partent
ensemble, déclenchent le quota, et chaque dépassement coûte de 5 à 20 s
d'attente. Mesuré sur le chargement d'une session, 3 essais consécutifs :
22,1 / 1,9 / 2,0 s sans espacement contre 1,8 / 1,7 / 1,8 s avec 0,05 s.

C'est le pic qui faisait tomber l'application, pas la moyenne.
"""
from __future__ import annotations

import io
import json

import pytest

from src import openf1


class _Reponse(io.BytesIO):
    """Minimum viable pour `with urlopen(...) as r: r.read()`."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture(autouse=True)
def _debit_neutre():
    """Remet le limiteur à zéro : c'est un état de module.

    Sans cela, un test qui émet une requête décale la temporisation du
    suivant, et les assertions sur `time.sleep` dépendent de l'ordre
    d'exécution.
    """
    openf1.reinitialiser_debit()
    yield
    openf1.reinitialiser_debit()


@pytest.fixture
def api_qui_repond(monkeypatch):
    def faux_urlopen(requete, timeout=None):
        return _Reponse(json.dumps([{"ok": True}]).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", faux_urlopen)


def test_la_premiere_requete_part_sans_attendre(monkeypatch, api_qui_repond):
    pauses = []
    monkeypatch.setattr(openf1.time, "sleep", pauses.append)

    openf1._get("sessions", year=2026)

    assert not any(p > 0 for p in pauses), "rien ne justifie d'attendre au premier appel"


def test_les_requetes_suivantes_sont_espacees(monkeypatch, api_qui_repond):
    pauses = []
    monkeypatch.setattr(openf1.time, "sleep", pauses.append)
    monkeypatch.setattr(openf1, "_INTERVALLE_MIN_REQUETES", 0.5)
    openf1.reinitialiser_debit()

    openf1._get("sessions", year=2026)
    openf1._get("drivers", session_key=1)

    attentes = [p for p in pauses if p > 0]
    assert attentes, "la seconde requête doit patienter"
    assert max(attentes) <= 0.5, "l'attente ne doit pas excéder l'intervalle demandé"


def test_l_espacement_reste_mesure():
    """Garde-fou : trop d'espacement coûte plus cher que le quota évité.

    Mesures (7 endpoints, 3 essais, cache neutralisé) : 0,05 s → 1,8 s stable ;
    0,10 s → jusqu'à 3,3 s ; 0,15 s → jusqu'à 3,1 s. Augmenter ce réglage
    « par prudence » dégrade donc les performances : toute modification doit
    être remesurée, pas estimée.
    """
    assert 0 < openf1._INTERVALLE_MIN_REQUETES <= 0.1


def test_reinitialiser_debit_oublie_le_dernier_depart(monkeypatch, api_qui_repond):
    monkeypatch.setattr(openf1.time, "sleep", lambda _: None)
    openf1._get("sessions", year=2026)

    openf1.reinitialiser_debit()

    assert openf1._dernier_depart == 0.0


def test_le_limiteur_nempeche_pas_de_recuperer_les_donnees(api_qui_repond):
    """Le limiteur ne doit pas altérer le contenu renvoyé."""
    assert openf1._get("sessions", year=2026) == [{"ok": True}]
