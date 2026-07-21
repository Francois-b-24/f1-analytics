"""Tests de non-régression sur les figures matplotlib.

100 % offline : les figures consomment des DataFrames, pas de session FastF1.
Couvre notamment la grille à 22 voitures introduite en 2026, qui cassait
l'ancien `set_ylim([20.5, 0.5])` codé en dur.
"""
import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")  # backend sans affichage, obligatoire en CI

from src.data import figure_positions_par_tour  # noqa: E402


def _fake_laps(nb_pilotes: int, nb_tours: int = 10) -> pd.DataFrame:
    """Construit un DataFrame de tours pour `nb_pilotes` pilotes.

    Chaque pilote garde une position constante égale à son rang, ce qui rend
    la position maximale exactement égale à `nb_pilotes`.
    """
    lignes = []
    for rang in range(1, nb_pilotes + 1):
        code = f"D{rang:02d}"
        for tour in range(1, nb_tours + 1):
            lignes.append({"Driver": code, "LapNumber": tour, "Position": float(rang)})
    return pd.DataFrame(lignes)


@pytest.mark.parametrize("nb_pilotes", [20, 22])
def test_positions_axe_suit_la_grille(nb_pilotes):
    """L'axe des positions doit s'adapter à la taille réelle de la grille."""
    fig = figure_positions_par_tour(_fake_laps(nb_pilotes))
    ax = fig.axes[0]

    bas, haut = ax.get_ylim()
    # Axe inversé : la position 1 est en haut
    assert haut == pytest.approx(0.5)
    assert bas == pytest.approx(nb_pilotes + 0.5)

    ticks = [int(t) for t in ax.get_yticks()]
    assert ticks[0] == 1
    # Le dernier pilote de la grille doit être visible sur l'axe
    assert ticks[-1] == nb_pilotes
    matplotlib.pyplot.close(fig)


def test_positions_grille_2026_inclut_toutes_les_voitures():
    """Régression 2026 : avec 22 voitures, aucune ne doit sortir du cadre."""
    fig = figure_positions_par_tour(_fake_laps(22))
    ax = fig.axes[0]

    bas, _ = ax.get_ylim()
    assert bas >= 22, "La 22e position est hors du cadre (ancien ylim figé à 20.5)"
    # Une courbe par pilote
    assert len(ax.lines) == 22
    matplotlib.pyplot.close(fig)


def test_positions_session_vide_renvoie_une_figure():
    """Une session sans tours ne doit pas lever, mais rendre une figure d'erreur."""
    fig = figure_positions_par_tour(pd.DataFrame(columns=["Driver", "LapNumber", "Position"]))
    assert fig is not None
    assert len(fig.axes) >= 1
    matplotlib.pyplot.close(fig)
