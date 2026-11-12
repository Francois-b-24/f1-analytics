"""Fixtures partagées et hygiène d'exécution de la suite.

Ce fichier ne déplace **pas** les fixtures locales de `test_adaptateurs.py` et
`test_analytics.py` : elles décrivent des entrées précises, propres à leurs
assertions, et les centraliser les rendrait moins lisibles sans rien
factoriser d'utile.

Il porte en revanche ce qui est réellement transverse :

- `session_factice`, le dict au contrat de `chargement_session`, utile dès
  qu'un test a besoin d'une session sans réseau ;
- la purge des caches Streamlit entre tests, sans laquelle un `st.cache_data`
  rempli par un test fausse le suivant (ils partagent le même processus).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def _caches_vides():
    """Vide les caches Streamlit autour de chaque test.

    `AppTest` s'exécute dans le processus pytest : sans cette purge, une
    session mise en cache par un test resurgirait dans un autre et masquerait
    une régression.
    """
    st.cache_data.clear()
    st.cache_resource.clear()
    yield
    st.cache_data.clear()
    st.cache_resource.clear()


@pytest.fixture
def tours_factices() -> pd.DataFrame:
    """Tours de deux pilotes, deux écuries, avec relais et arrêt.

    Colonnes conformes à `adaptateurs.COLONNES_TOURS` : un test qui s'appuie
    dessus vérifie donc le même schéma que celui produit en production.
    """
    return pd.DataFrame({
        "Driver": ["VER"] * 6 + ["HAM"] * 6,
        "DriverNumber": [1] * 6 + [44] * 6,
        "Team": ["Red Bull"] * 6 + ["Mercedes"] * 6,
        "LapNumber": list(range(1, 7)) * 2,
        "LapTime": pd.to_timedelta([80.1, 79.8, 79.5, 80.2, 79.9, 79.7] * 2, unit="s"),
        "LapSeconds": [80.1, 79.8, 79.5, 80.2, 79.9, 79.7] * 2,
        "Sector1TimeSec": [26.0] * 12,
        "Sector2TimeSec": [27.0] * 12,
        "Sector3TimeSec": [26.5] * 12,
        "Compound": ["SOFT"] * 3 + ["HARD"] * 3 + ["SOFT"] * 3 + ["MEDIUM"] * 3,
        "Stint": [1, 1, 1, 2, 2, 2] * 2,
        "TyreLife": [1, 2, 3, 1, 2, 3] * 2,
        # PitInTime porte la *durée* d'immobilisation, pas un instant
        # (cf. adaptateurs.construire_tours).
        "PitInTime": pd.to_timedelta(
            [None, None, None, 2.4, None, None,
             None, None, None, 3.1, None, None], unit="s",
        ),
        "PitOutTime": [pd.NaT] * 12,
        "IsPersonalBest": [False, False, True, False, False, False] * 2,
        # VER remonte de la 3e à la 1re place, HAM descend de la 1re à la 2e.
        "Position": [3.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0],
    })


@pytest.fixture
def meteo_factice() -> pd.DataFrame:
    return pd.DataFrame({
        "SessionTimeSec": [0, 60, 120],
        "AirTemp": [22.0, 22.5, 23.0],
        "TrackTemp": [35.0, 36.0, 37.0],
        "WindSpeed": [1.0, 1.2, 0.9],
    })


@pytest.fixture
def resultats_factices() -> pd.DataFrame:
    return pd.DataFrame({
        "Position": [1, 2],
        "Abbreviation": ["VER", "HAM"],
        "TeamName": ["Red Bull", "Mercedes"],
        "Points": [25.0, 18.0],
        "Status": ["Terminé"] * 2,
        "Laps": [6, 6],
    })


@pytest.fixture
def telemetrie_factice() -> pd.DataFrame:
    """Tour synthétique : freinage au début, puis montée en vitesse."""
    n = 300
    return pd.DataFrame({
        "Distance": np.linspace(0, 5000, n),
        "Speed": np.linspace(80, 320, n),
        "Throttle": np.clip(np.linspace(0, 100, n), 0, 100),
        "Brake": [True] * 30 + [False] * (n - 30),
        "nGear": np.clip(np.linspace(1, 8, n).astype(int), 1, 8),
        "RPM": np.linspace(9000, 12000, n),
        # Vérifié sur données réelles : ce canal ne contient que des zéros.
        "DRS": [0] * n,
        "X": np.cos(np.linspace(0, 6.28, n)) * 1000,
        "Y": np.sin(np.linspace(0, 6.28, n)) * 1000,
        "Time": pd.to_timedelta(np.linspace(0, 80, n), unit="s"),
    })


@pytest.fixture
def session_factice(
    tours_factices, meteo_factice, resultats_factices
) -> dict:
    """Dict au contrat exact de `chargement_session`.

    `best_laps` est un **dict** {code pilote: infos}, pas un DataFrame — se
    tromper ici produit un « truth value of a DataFrame is ambiguous »
    difficile à rattacher à sa cause.
    """
    best_laps = {
        code: {
            "LapNumber": 3,
            "LapSeconds": 79.5,
            "LapTimeStr": "1:19.500",
            "DriverNumber": 1 if code == "VER" else 44,
            "debut": "2024-01-01T00:00:00",
            "duree": 79.5,
            "Compound": "SOFT",
            "Stint": 1,
        }
        for code in ("VER", "HAM")
    }
    return {
        "nom": "GP test",
        "tours": tours_factices,
        "pilotes": ["VER", "HAM"],
        "meteo": meteo_factice,
        "resultats": resultats_factices,
        "best_laps": best_laps,
        "session_key": 9999,
        "session": None,
    }
