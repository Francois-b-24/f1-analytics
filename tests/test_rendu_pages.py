"""Rendu réel des pages, hors ligne — le filet qui manquait.

Pourquoi ce fichier
-------------------
La production a déjà servi une app sans aucune page, puis une app dont les dix
onglets levaient `StreamlitPageNotFoundError`, sans que lint, tests ni CI ne
bronchent. Le post-mortem de l'époque le dit : la validation reposait sur du
lint et des tests unitaires, et rien n'exerçait le rendu d'une page.

`tests/test_points_entree.py` garde les invariants *statiques* (fichiers
présents, pages déclarées, pas de `page_link` par chemin). Ces tests-ci
complètent par le seul contrôle qui aurait attrapé la panne : on **monte
réellement** chaque page avec `AppTest` et on vérifie qu'aucune exception n'est
levée.

Contraintes de conception
-------------------------
* **Strictement hors ligne.** `src/openf1.py::_get` est le seul point de sortie
  réseau de l'application : le neutraliser suffit. Une CI qui dépend du réseau
  devient instable, et une CI rouge gèle le redéploiement Streamlit Cloud.
* **Une page qui s'arrête proprement est un succès.** Sans session chargée, une
  page affiche son état vide et appelle `st.stop()` : c'est le comportement
  attendu, pas un échec. On n'assert que l'absence d'exception.
* `AppTest` seul ne met pas la racine du dépôt dans `sys.path` ; c'est
  `pythonpath = ["."]` (pyproject.toml) qui le fait sous pytest. Ces tests ne
  fonctionnent donc que lancés par pytest, ce qui est le seul mode utilisé.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.navigation import _DECLARATION

RACINE = Path(__file__).resolve().parent.parent

# Généreux à dessein : la CI partagée est lente, et un timeout trop court
# produirait des échecs intermittents — donc une prod gelée pour rien.
DELAI = 60


@pytest.fixture
def sans_reseau(monkeypatch):
    """Coupe l'unique sortie réseau et compte les tentatives d'appel.

    Retourne la liste des endpoints sollicités, pour que les tests puissent
    affirmer non seulement « ça rend » mais « ça rend sans réseau ».
    """
    appels: list[str] = []

    def _faux_get(endpoint: str, **params) -> list[dict]:
        appels.append(endpoint)
        return []

    monkeypatch.setattr("src.openf1._get", _faux_get)
    return appels


@pytest.mark.parametrize("fichier", [nom for nom, _, _ in _DECLARATION])
def test_page_rend_sans_exception(fichier, sans_reseau):
    """Chaque page se monte sans lever, même sans session chargée.

    C'est le test qui aurait vu les dix onglets cassés : `lien_accueil()`
    levait `StreamlitPageNotFoundError` à chaque rendu d'état vide.
    """
    app = AppTest.from_file(str(RACINE / "pages" / fichier), default_timeout=DELAI)
    app.run()
    assert not app.exception, [e.value for e in app.exception]


def test_routeur_rend_sans_exception(sans_reseau):
    """Le routeur monte la navigation et rend la page par défaut."""
    app = AppTest.from_file(str(RACINE / "streamlit_app.py"), default_timeout=DELAI)
    app.run()
    assert not app.exception, [e.value for e in app.exception]


def test_accueil_rend_sans_exception(sans_reseau):
    """`Home.py` est aussi un point d'entrée possible côté hébergeur.

    Le « Main file path » est configuré chez Streamlit Cloud, hors du dépôt :
    les deux entrées doivent rendre.
    """
    app = AppTest.from_file(str(RACINE / "Home.py"), default_timeout=DELAI)
    app.run()
    assert not app.exception, [e.value for e in app.exception]


@pytest.mark.parametrize("fichier", [nom for nom, _, _ in _DECLARATION])
def test_page_ne_sollicite_pas_le_reseau_sans_session(fichier, sans_reseau):
    """Sans session demandée, une page ne déclenche aucun appel OpenF1.

    Garde-fou de coût : les sondes keep-alive et les robots atteignent ces
    pages. Un chargement de session non sollicité coûte sept requêtes et
    mord sur le quota (HTTP 429) — pour tout le monde, y compris nous.
    """
    app = AppTest.from_file(str(RACINE / "pages" / fichier), default_timeout=DELAI)
    app.run()
    assert sans_reseau == [], f"Appels réseau non sollicités : {sans_reseau}"


# ---------------------------------------------------------------------------
# Rendu avec une session chargée
#
# Les tests ci-dessus montent les pages sans session : elles s'arrêtent alors
# sur leur état vide, et seul le préambule est exercé. C'est insuffisant — le
# corps des pages (Plotly, matplotlib, agrégations pandas) n'est jamais
# exécuté, et c'est précisément là qu'une refonte casse quelque chose.
#
# On injecte donc une session synthétique conforme au contrat de
# `chargement_session`, pour que chaque page s'exécute jusqu'au bout sans
# toucher au réseau.
# ---------------------------------------------------------------------------

_PILOTES = ("VER", "NOR", "LEC")


def _tours_synthetiques() -> pd.DataFrame:
    """Trois pilotes, huit tours, deux relais, un arrêt — assez pour tout tracer."""
    lignes = []
    for rang, code in enumerate(_PILOTES):
        for tour in range(1, 9):
            secondes = 92.0 + rang * 0.4 + (0.05 * tour)
            lignes.append({
                "Driver": code,
                "DriverNumber": 1 + rang,
                "Team": f"Team {rang}",
                "LapNumber": tour,
                "LapTime": pd.to_timedelta(secondes, unit="s"),
                "LapSeconds": secondes,
                "Sector1TimeSec": secondes * 0.3,
                "Sector2TimeSec": secondes * 0.45,
                "Sector3TimeSec": secondes * 0.25,
                "Compound": "SOFT" if tour <= 4 else "MEDIUM",
                "Stint": 1 if tour <= 4 else 2,
                "TyreLife": tour if tour <= 4 else tour - 4,
                # Un unique arrêt au tour 5, pour que la page Arrêts ait de la matière.
                "PitInTime": pd.to_timedelta(secondes, unit="s") if tour == 5 else pd.NaT,
                "PitOutTime": pd.NaT,
                "IsPersonalBest": tour == 2,
                "Position": float(rang + 1),
            })
    return pd.DataFrame(lignes)


def _session_synthetique() -> dict:
    """Reproduit le contrat exact renvoyé par `chargement_session`."""
    tours = _tours_synthetiques()
    meteo = pd.DataFrame({
        "SessionTimeSec": np.arange(0.0, 300.0, 60.0),
        "AirTemp": [24.0, 24.2, 24.5, 24.4, 24.1],
        "TrackTemp": [38.0, 38.6, 39.1, 38.8, 38.2],
        "Humidity": [40.0, 41.0, 42.0, 41.5, 40.5],
        "Pressure": [1011.0] * 5,
        "WindSpeed": [3.0, 3.4, 3.1, 2.8, 3.2],
        "WindDirection": [180.0, 182.0, 179.0, 181.0, 180.0],
        "Rainfall": [0.0] * 5,
    })
    resultats = pd.DataFrame({
        "Position": [1.0, 2.0, 3.0],
        "Driver": list(_PILOTES),
        "BroadcastName": ["M VERSTAPPEN", "L NORRIS", "C LECLERC"],
        "DriverNumber": [1, 4, 16],
        "TeamName": ["Red Bull Racing", "McLaren", "Ferrari"],
        "Points": [25.0, 18.0, 15.0],
        "Status": ["Finished"] * 3,
        "Time": [pd.to_timedelta(5400, unit="s")] * 3,
        "FastestLapTime": [pd.to_timedelta(92.0, unit="s")] * 3,
    })
    return {
        "nom": "Grand Prix de test",
        "tours": tours,
        "pilotes": list(_PILOTES),
        "meteo": meteo,
        "resultats": resultats,
        "best_laps": {
            code: {"DriverNumber": 1 + rang, "LapNumber": 2,
                   "debut": "2026-07-19T13:05:44.573000+00:00",
                   "fin": "2026-07-19T13:07:16.573000+00:00"}
            for rang, code in enumerate(_PILOTES)
        },
        "session_key": 9999,
        "session": None,
    }


def _telemetrie_synthetique() -> pd.DataFrame:
    """Un tour de télémétrie plausible : vitesse, rapports, freinage, tracé."""
    n = 200
    distance = np.linspace(0.0, 5000.0, n)
    vitesse = 120.0 + 180.0 * np.abs(np.sin(np.linspace(0, 3 * np.pi, n)))
    return pd.DataFrame({
        "Distance": distance,
        "Speed": vitesse,
        "nGear": np.clip((vitesse // 50).astype(int), 1, 8),
        "Brake": (vitesse < 160).astype(int),
        "Throttle": np.clip(vitesse / 3.0, 0, 100),
        "RPM": 8000 + vitesse * 10,
        "DRS": np.zeros(n, dtype=int),
        "X": np.cos(np.linspace(0, 2 * np.pi, n)) * 1000,
        "Y": np.sin(np.linspace(0, 2 * np.pi, n)) * 1000,
        "Time": pd.to_timedelta(np.linspace(0, 92, n), unit="s"),
        "SessionTimeSec": np.linspace(0, 92, n),
    })


@pytest.fixture
def session_chargee(monkeypatch, sans_reseau):
    """Simule une session chargée, sans aucun appel réseau.

    Les fonctions sont patchées là où elles sont *définies* (`src.data`) : les
    pages les importent directement dans leur espace de noms, donc patcher le
    module d'origine avant leur exécution couvre les deux formes d'import.
    """
    donnees = _session_synthetique()
    tel = _telemetrie_synthetique()

    monkeypatch.setattr("src.data.chargement_session", lambda *a, **k: donnees)
    monkeypatch.setattr("src.data.telemetrie_pilote", lambda *a, **k: tel)
    monkeypatch.setattr("src.data.tour_rapide_tel", lambda *a, **k: tel)
    return donnees


def _etat_session_chargee() -> dict:
    """Les quatre clés que les pages lisent pour se croire prêtes."""
    return {"annee": 2026, "grand_prix": "Grand Prix de test",
            "session_type": "R", "loaded": True}


@pytest.mark.parametrize("fichier", [nom for nom, _, _ in _DECLARATION])
def test_page_rend_avec_session_chargee(fichier, session_chargee):
    """Chaque page s'exécute jusqu'au bout sur une session complète.

    C'est le test qui exerce réellement le corps des pages — graphiques
    Plotly, figures matplotlib, agrégations. Sans session, les pages
    s'arrêtent sur leur état vide et ne prouvent presque rien.
    """
    app = AppTest.from_file(str(RACINE / "pages" / fichier), default_timeout=DELAI)
    for cle, valeur in _etat_session_chargee().items():
        app.session_state[cle] = valeur
    app.run()
    assert not app.exception, [e.value for e in app.exception]


def test_accueil_rend_avec_session_chargee(session_chargee):
    """L'accueil affiche ses KPI, son top 10 et ses graphiques sans lever."""
    app = AppTest.from_file(str(RACINE / "Home.py"), default_timeout=DELAI)
    for cle, valeur in _etat_session_chargee().items():
        app.session_state[cle] = valeur
    app.run()
    assert not app.exception, [e.value for e in app.exception]


def test_home_lance_directement_delegue_sans_import_error(sans_reseau, monkeypatch):
    """`Home.py` lancé comme point d'entrée rend l'app, sans ImportError.

    Ce chemin exécute `Home.py` deux fois dans la même pile : lancé
    directement il délègue au routeur par `runpy.run_path`, lequel réexécute
    `streamlit_app.py` dans un espace de noms neuf et rend l'accueil — donc
    relance `Home.py`.

    La production a cassé exactement là : `from src.ui import barre_contexte`
    levait `ImportError` au second passage. Ce test couvre le chemin, mais
    honnêteté sur sa portée — il ne reproduit pas la panne : ni AppTest ni un
    `runpy` en interpréteur froid ne la déclenchent hors de Streamlit Cloud.
    Seul `Home.py` important `src.ui` comme module, et non ses symboles, rend
    ce chemin insensible à l'ordre d'initialisation.

    Les modules du paquet sont retirés de `sys.modules` pour partir au plus
    près d'un interpréteur froid, les imports déjà résolus par les tests
    précédents masquant une partie du chemin.
    """
    import sys

    for nom in [n for n in sys.modules if n == "src" or n.startswith("src.")]:
        monkeypatch.delitem(sys.modules, nom, raising=False)

    app = AppTest.from_file(str(RACINE / "Home.py"), default_timeout=DELAI)
    app.run()

    messages = [e.value for e in app.exception]
    assert not any("ImportError" in str(m) or "cannot import name" in str(m)
                   for m in messages), messages
    assert not app.exception, messages
