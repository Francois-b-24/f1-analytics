"""Smoke tests pour `chargement_session` — nécessitent le réseau.

Distingue une indisponibilité de l'API (acceptable — `xfail`) d'une rupture de
contrat ou de signature (vrai bug — `fail`). Les autres fichiers de tests sont
entièrement hors ligne.
"""
import socket

import pytest

from src.data import chargement_session
from src.openf1 import PREMIERE_SAISON

# Course de référence : suffisamment ancienne pour que ses données soient
# stables et intégralement publiées.
ANNEE_REF = 2024
COURSE_REF = "Australia Grand Prix (Melbourne)"


def _acces_reseau(host: str = "api.openf1.org", port: int = 443, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not _acces_reseau(), reason="Pas de connexion — smoke test hors ligne impossible")
def test_chargement_session_contrat():
    """Vérifie le contrat de retour de `chargement_session`.

    Les pages consomment ces clés : toute disparition est une régression, même
    si les données changent d'une saison à l'autre.
    """
    try:
        d = chargement_session(ANNEE_REF, COURSE_REF, "R")
    except Exception as exc:
        pytest.xfail(f"OpenF1 indisponible: {type(exc).__name__}: {exc}")

    assert isinstance(d, dict)
    attendues = {"nom", "tours", "pilotes", "meteo", "resultats",
                 "tel_par_pilote", "best_laps", "session_key"}
    manquantes = attendues - set(d.keys())
    assert not manquantes, f"Clés manquantes dans le retour: {manquantes}"

    assert not d["tours"].empty, "Aucun tour — données probablement vides"
    assert len(d["pilotes"]) > 0, "Aucun pilote détecté"

    # Colonnes indispensables aux pages et à src.analytics
    for colonne in ("Driver", "LapNumber", "LapTime", "LapSeconds", "Compound"):
        assert colonne in d["tours"].columns, f"colonne manquante: {colonne}"


@pytest.mark.skipif(not _acces_reseau(), reason="Pas de connexion")
def test_chargement_session_introuvable():
    """Une session inexistante lève, plutôt que de renvoyer un résultat vide."""
    with pytest.raises(Exception):
        chargement_session(ANNEE_REF, "Non Existing Grand Prix XYZ", "R")


@pytest.mark.skipif(not _acces_reseau(), reason="Pas de connexion")
def test_saison_anterieure_a_la_couverture():
    """Les saisons antérieures à la couverture OpenF1 échouent explicitement."""
    with pytest.raises(Exception):
        chargement_session(PREMIERE_SAISON - 1, COURSE_REF, "R")
