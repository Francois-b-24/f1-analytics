"""Tests du client HTTP OpenF1 — hors ligne, par injection sur urlopen.

C'est la logique la plus subtile du projet (retry, quota, encodage des
opérateurs de filtre) et elle n'était couverte par aucun test : une régression
ici casse toute l'application en production sans qu'aucun test ne rougisse.

Aucun test de ce module ne touche le réseau : `urllib.request.urlopen` est
systématiquement remplacé.
"""
from __future__ import annotations

import io
import json
import urllib.error

import pytest

from src import openf1


class _Reponse(io.BytesIO):
    """Minimum viable pour le `with urlopen(...) as reponse: reponse.read()`."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _repondre(monkeypatch, charge):
    """Fait répondre urlopen avec `charge` (sérialisée en JSON)."""
    def faux_urlopen(requete, timeout=None):
        return _Reponse(json.dumps(charge).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", faux_urlopen)


def _lever(monkeypatch, exception, *, compteur=None):
    """Fait échouer urlopen avec `exception`, en comptant les tentatives."""
    def faux_urlopen(requete, timeout=None):
        if compteur is not None:
            compteur.append(1)
        raise exception

    monkeypatch.setattr("urllib.request.urlopen", faux_urlopen)


def _http_error(code, headers=None):
    return urllib.error.HTTPError(
        url="https://api.openf1.org/v1/laps",
        code=code,
        msg="erreur simulée",
        hdrs=headers or {},
        fp=None,
    )


# --------------------------------------------------------------------------
# Construction d'URL
# --------------------------------------------------------------------------

def test_les_operateurs_de_filtre_ne_sont_pas_encodes():
    """OpenF1 filtre avec `date>=...` : un encodage classique casserait tout.

    Si `>` devenait `%3E`, l'API renverrait la session entière — soit ~5,5 Mo
    par pilote au lieu de ~90 Ko.
    """
    url = openf1._construire_url("car_data", {"date>": "2026-07-19T13:00:00"})

    assert "date>=" in url or "date>" in url
    assert "%3E" not in url


def test_les_parametres_nuls_sont_omis():
    url = openf1._construire_url("laps", {"session_key": 42, "driver_number": None})

    assert "session_key=42" in url
    assert "driver_number" not in url


def test_sans_parametre_aucun_point_dinterrogation():
    assert openf1._construire_url("sessions", {}) == f"{openf1.BASE_URL}/sessions"


# --------------------------------------------------------------------------
# Codes de retour
# --------------------------------------------------------------------------

def test_404_signifie_pas_de_donnees_et_non_une_panne(monkeypatch):
    """Un 404 est traduit en liste vide : c'est un cas métier, pas une erreur."""
    _lever(monkeypatch, _http_error(404))

    assert openf1._get("laps", session_key=1) == []


def test_reponse_json_valide_est_retournee_telle_quelle(monkeypatch):
    _repondre(monkeypatch, [{"lap_number": 1}, {"lap_number": 2}])

    assert openf1._get("laps", session_key=1) == [{"lap_number": 1}, {"lap_number": 2}]


def test_un_objet_au_lieu_dune_liste_est_une_erreur(monkeypatch):
    """OpenF1 renvoie un dict pour signaler une erreur applicative."""
    _repondre(monkeypatch, {"detail": "quota dépassé"})

    with pytest.raises(openf1.OpenF1Indisponible, match="Réponse inattendue"):
        openf1._get("laps", session_key=1)


def test_4xx_autre_que_404_narrete_pas_de_reessayer_inutilement(monkeypatch):
    """Un 400 ne sera pas corrigé par une nouvelle tentative."""
    tentatives = []
    _lever(monkeypatch, _http_error(400), compteur=tentatives)

    with pytest.raises(openf1.OpenF1Indisponible):
        openf1._get("laps", session_key=1)

    assert len(tentatives) == 1, "un 4xx ne doit pas être réessayé"


def test_5xx_est_reessaye_jusqua_epuisement(monkeypatch):
    tentatives = []
    monkeypatch.setattr(openf1, "_ATTENTE_ENTRE_TENTATIVES", 0)
    _lever(monkeypatch, _http_error(503), compteur=tentatives)

    with pytest.raises(openf1.OpenF1Indisponible):
        openf1._get("laps", session_key=1)

    assert len(tentatives) == openf1._TENTATIVES


def test_erreur_reseau_est_reessayee_puis_signalee(monkeypatch):
    tentatives = []
    monkeypatch.setattr(openf1, "_ATTENTE_ENTRE_TENTATIVES", 0)
    _lever(monkeypatch, urllib.error.URLError("connexion refusée"), compteur=tentatives)

    with pytest.raises(openf1.OpenF1Indisponible, match="Impossible de joindre"):
        openf1._get("laps", session_key=1)

    assert len(tentatives) == openf1._TENTATIVES


def test_succes_apres_un_echec_transitoire(monkeypatch):
    """Le retry doit effectivement rattraper une panne passagère."""
    etat = {"appels": 0}
    monkeypatch.setattr(openf1, "_ATTENTE_ENTRE_TENTATIVES", 0)

    def faux_urlopen(requete, timeout=None):
        etat["appels"] += 1
        if etat["appels"] == 1:
            raise urllib.error.URLError("coupure passagère")
        return _Reponse(json.dumps([{"ok": True}]).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", faux_urlopen)

    assert openf1._get("laps", session_key=1) == [{"ok": True}]
    assert etat["appels"] == 2


# --------------------------------------------------------------------------
# Quota (429)
# --------------------------------------------------------------------------

def test_le_quota_respecte_le_retry_after(monkeypatch):
    attentes = []
    monkeypatch.setattr(openf1.time, "sleep", attentes.append)
    monkeypatch.setattr(openf1.random, "uniform", lambda a, b: 0.0)
    _lever(monkeypatch, _http_error(429, {"retry-after": "7"}))

    with pytest.raises(openf1.OpenF1Indisponible):
        openf1._get("laps", session_key=1)

    assert attentes and attentes[0] == pytest.approx(7.0)


def test_le_quota_est_plafonne(monkeypatch):
    """Un `retry-after` démesuré ne doit pas figer l'application."""
    attentes = []
    monkeypatch.setattr(openf1.time, "sleep", attentes.append)
    monkeypatch.setattr(openf1.random, "uniform", lambda a, b: 0.0)
    _lever(monkeypatch, _http_error(429, {"retry-after": "3600"}))

    with pytest.raises(openf1.OpenF1Indisponible):
        openf1._get("laps", session_key=1)

    assert max(attentes) <= openf1._ATTENTE_QUOTA_MAX


def test_retry_after_illisible_retombe_sur_le_defaut(monkeypatch):
    attentes = []
    monkeypatch.setattr(openf1.time, "sleep", attentes.append)
    monkeypatch.setattr(openf1.random, "uniform", lambda a, b: 0.0)
    _lever(monkeypatch, _http_error(429, {"retry-after": "bientôt"}))

    with pytest.raises(openf1.OpenF1Indisponible):
        openf1._get("laps", session_key=1)

    assert attentes[0] == pytest.approx(openf1._ATTENTE_QUOTA_DEFAUT)


def test_le_jitter_est_applique_sur_le_quota(monkeypatch):
    """Sans décalage, les threads parallèles re-saturent le quota ensemble."""
    attentes = []
    monkeypatch.setattr(openf1.time, "sleep", attentes.append)
    monkeypatch.setattr(openf1.random, "uniform", lambda a, b: 0.42)
    _lever(monkeypatch, _http_error(429, {"retry-after": "5"}))

    with pytest.raises(openf1.OpenF1Indisponible):
        openf1._get("laps", session_key=1)

    assert attentes[0] == pytest.approx(5.42)


# --------------------------------------------------------------------------
# Hiérarchie d'exceptions
# --------------------------------------------------------------------------

def test_les_sous_classes_restent_compatibles():
    """Tout `except OpenF1Error` ou `except RuntimeError` existant tient."""
    assert issubclass(openf1.OpenF1Indisponible, openf1.OpenF1Error)
    assert issubclass(openf1.OpenF1SansDonnees, openf1.OpenF1Error)
    assert issubclass(openf1.OpenF1Error, RuntimeError)


# --------------------------------------------------------------------------
# Limitation de débit
# --------------------------------------------------------------------------

def test_les_requetes_sont_espacees(monkeypatch):
    """OpenF1 répond 429 au-delà de ~4 requêtes par demi-seconde.

    Sans espacement, une requête sur cinq échouait et déclenchait une attente
    de 5 à 20 s — bien plus coûteuse que la pause elle-même.
    """
    pauses = []
    monkeypatch.setattr(openf1.time, "sleep", pauses.append)
    monkeypatch.setattr(openf1, "_INTERVALLE_MIN_REQUETES", 0.5)
    openf1.reinitialiser_debit()
    _repondre(monkeypatch, [{"ok": True}])

    openf1._get("sessions", year=2026)
    openf1._get("sessions", year=2026)

    # La première requête part sans attendre, la seconde patiente.
    assert pauses, "la seconde requête doit être espacée de la première"
    assert pauses[-1] <= 0.5


def test_l_espacement_reste_mesure():
    """Garde-fou : trop d'espacement coûte plus cher que le quota.

    Mesuré sur le chargement des 7 endpoints d'une session, cache neutralisé :
    0,10 s → 2,8 s ; 0,20 s → 2,9 s ; 0,30 s → 42,9 s. La valeur ne doit donc
    pas être augmentée « par prudence » sans remesurer.
    """
    assert 0 < openf1._INTERVALLE_MIN_REQUETES <= 0.2


def test_reinitialiser_debit_oublie_le_dernier_appel(monkeypatch):
    monkeypatch.setattr(openf1.time, "sleep", lambda _: None)
    _repondre(monkeypatch, [{"ok": True}])
    openf1._get("sessions", year=2026)

    openf1.reinitialiser_debit()

    assert openf1._dernier_appel == 0.0
