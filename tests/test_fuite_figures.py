"""Les figures matplotlib ne doivent rien laisser derrière elles — hors ligne.

Incident vécu : la page Performances faisait tuer le processus après quelques
visites, sans aucune trace dans les logs (le système tue, il ne lève pas).
Deux causes cumulées, toutes deux mesurées :

1. `st.pyplot` ne ferme pas la figure qu'on lui passe : 8 visites laissaient
   8 figures ouvertes et +23 Mo non rendus.
2. `tight_layout()` retient de la mémoire avec le backend Agg et une légende
   hors des axes, même après `plt.close(fig)` : +30 Mo sur 30 figures, contre
   +6 Mo avec `layout="constrained"`.

Sous le plafond mémoire de Streamlit Cloud (~1 Go), ces deux fuites suffisent
à rendre l'application inutilisable à l'usage.
"""
from __future__ import annotations

import gc
import resource

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.data import figure_positions_par_tour  # noqa: E402
from src.ui import afficher_figure  # noqa: E402


def _memoire_mo() -> float:
    brut = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS compte en octets, Linux en kilo-octets.
    return brut / 1048576 if brut > 1e7 else brut / 1024


@pytest.fixture(autouse=True)
def _aucune_figure_residuelle():
    plt.close("all")
    yield
    plt.close("all")


@pytest.fixture
def tours() -> pd.DataFrame:
    """22 pilotes sur 60 tours : l'ordre de grandeur d'une vraie course."""
    pilotes = [f"P{i:02d}" for i in range(22)]
    lignes = []
    for rang, code in enumerate(pilotes):
        for tour in range(1, 61):
            lignes.append({
                "Driver": code,
                "LapNumber": tour,
                "Position": float(((rang + tour) % 22) + 1),
            })
    return pd.DataFrame(lignes)


def test_afficher_figure_libere_la_figure():
    fig = plt.figure()
    assert plt.get_fignums() == [fig.number]

    afficher_figure(fig)

    assert plt.get_fignums() == [], "st.pyplot ne ferme pas : afficher_figure doit le faire"


def test_visites_repetees_naccumulent_pas_de_figures(tours):
    """Simule des visites successives de la page Performances."""
    for _ in range(25):
        plt.close(figure_positions_par_tour(tours))

    assert plt.get_fignums() == []


def test_la_figure_des_positions_ne_retient_pas_la_memoire(tours):
    """Garde-fou chiffré contre le retour de la fuite `tight_layout`.

    Avant correction : +63 Mo sur 30 appels. Après : +8 Mo. Le seuil est
    volontairement lâche (la mesure RSS est bruitée et ne redescend jamais
    vraiment), mais il attrape une régression d'un ordre de grandeur.
    """
    gc.collect()
    depart = _memoire_mo()

    for _ in range(30):
        plt.close(figure_positions_par_tour(tours))

    gc.collect()
    croissance = _memoire_mo() - depart

    assert croissance < 35, f"croissance de {croissance:.0f} Mo sur 30 figures"


def test_la_figure_nutilise_pas_tight_layout():
    """`tight_layout` fuit ici ; `layout="constrained"` fait le même travail.

    Vérification statique : la fuite est silencieuse et n'apparaît qu'à
    l'usage, donc un test de mémoire seul laisserait passer sa réintroduction
    sur une autre figure.
    """
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "src" / "data.py").read_text(
        encoding="utf-8"
    )
    lignes_actives = [
        ligne for ligne in source.splitlines()
        if "tight_layout" in ligne and not ligne.strip().startswith("#")
    ]

    assert not lignes_actives, f"tight_layout réintroduit : {lignes_actives}"


def test_les_figures_matplotlib_passent_par_un_backend_non_interactif():
    """Un backend GUI sur un serveur sans affichage échoue ou fuit."""
    assert matplotlib.get_backend().lower() == "agg"


def test_aucune_page_nappelle_st_pyplot_directement():
    """Tout passe par `afficher_figure`, qui garantit la fermeture."""
    from pathlib import Path

    racine = Path(__file__).resolve().parent.parent
    fautives = [
        chemin.name
        for chemin in racine.glob("pages/*.py")
        if "st.pyplot(" in chemin.read_text(encoding="utf-8")
    ]

    assert not fautives, f"ces pages court-circuitent afficher_figure : {fautives}"


def test_la_fixture_est_representative(tours):
    """Si la fixture rétrécissait, le test de mémoire perdrait son sens."""
    assert tours["Driver"].nunique() == 22
    assert tours["LapNumber"].max() == 60
    assert np.issubdtype(tours["Position"].dtype, np.floating)
