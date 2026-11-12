"""Vérifie qu'afficher une figure ne laisse rien derrière elle.

Contexte : `st.pyplot` ne ferme pas la figure qu'on lui passe. Chaque rerun en
accumulait donc une de plus dans le gestionnaire global de matplotlib, sous un
plafond mémoire d'environ 1 Go sur Streamlit Cloud.
"""
from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.ui import afficher_figure  # noqa: E402


@pytest.fixture(autouse=True)
def _repartir_de_zero():
    plt.close("all")
    yield
    plt.close("all")


def test_le_backend_est_non_interactif():
    """`src.data` doit imposer Agg à l'import, avant tout pyplot."""
    import src.data  # noqa: F401

    assert matplotlib.get_backend().lower() == "agg"


def test_afficher_figure_libere_la_figure():
    fig = plt.figure()
    assert plt.get_fignums() == [fig.number]

    afficher_figure(fig)

    assert plt.get_fignums() == [], "la figure n'a pas été fermée"


def test_affichages_repetes_ne_saccumulent_pas():
    """Simule des reruns successifs sur une page à cartes de circuit."""
    for _ in range(25):
        afficher_figure(plt.figure())

    assert plt.get_fignums() == []
