"""Tests des indicateurs d'arrêts et de positions — hors ligne.

Ces fonctions alimentent les pages « Arrêts aux stands » et « Positions par
tour ». Elles n'exploitent que des colonnes déjà présentes dans le dict de
session : aucun appel réseau supplémentaire.

Attention à la sémantique : `PitInTime` porte la **durée** d'immobilisation
(issue de `pit_duration` d'OpenF1), pas un instant — cf.
`adaptateurs.construire_tours`.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.analytics import (
    arrets_par_equipe,
    arrets_par_pilote,
    bilan_positions,
    changements_de_position,
    resume_arrets,
)


@pytest.fixture
def tours_avec_arrets() -> pd.DataFrame:
    """Deux pilotes, deux écuries, trois arrêts de durées distinctes."""
    return pd.DataFrame({
        "Driver": ["VER", "VER", "VER", "HAM", "HAM", "HAM"],
        "Team": ["RB"] * 3 + ["Mercedes"] * 3,
        "LapNumber": [1, 15, 30, 1, 14, 32],
        "Compound": ["SOFT", "HARD", "HARD", "SOFT", "MEDIUM", "HARD"],
        "PitInTime": pd.to_timedelta([None, 2.4, None, None, 3.1, 2.8], unit="s"),
    })


@pytest.fixture
def tours_course() -> pd.DataFrame:
    """VER gagne 2 places, HAM en perd 1, NOR reste stable."""
    return pd.DataFrame({
        "Driver": ["VER"] * 3 + ["HAM"] * 3 + ["NOR"] * 3,
        "LapNumber": [1, 2, 3] * 3,
        "Position": [3.0, 2.0, 1.0, 1.0, 1.0, 2.0, 5.0, 5.0, 5.0],
    })


# --------------------------------------------------------------------------
# Arrêts
# --------------------------------------------------------------------------

def test_arrets_par_pilote_ne_retient_que_les_tours_avec_arret(tours_avec_arrets):
    arrets = arrets_par_pilote(tours_avec_arrets)

    assert len(arrets) == 3
    assert set(arrets["Pilote"]) == {"VER", "HAM"}
    assert list(arrets.columns) == ["Pilote", "Tour", "Duree", "Equipe", "Composé"]


def test_arrets_par_pilote_convertit_la_duree_en_secondes(tours_avec_arrets):
    arrets = arrets_par_pilote(tours_avec_arrets)

    assert arrets["Duree"].min() == pytest.approx(2.4)
    assert arrets["Duree"].max() == pytest.approx(3.1)


def test_arrets_par_pilote_ignore_les_durees_nulles():
    """Une durée de 0 traduit une donnée absente, pas un arrêt instantané."""
    tours = pd.DataFrame({
        "Driver": ["VER", "HAM"],
        "LapNumber": [10, 12],
        "PitInTime": pd.to_timedelta([0.0, 2.5], unit="s"),
    })

    arrets = arrets_par_pilote(tours)

    assert len(arrets) == 1
    assert arrets["Pilote"].iloc[0] == "HAM"


@pytest.mark.parametrize(
    "tours",
    [
        pd.DataFrame(),
        pd.DataFrame({"Driver": ["VER"], "LapNumber": [1]}),  # pas de PitInTime
        pd.DataFrame({"Driver": ["VER"], "LapNumber": [1], "PitInTime": [pd.NaT]}),
    ],
    ids=["vide", "colonne_absente", "aucun_arret"],
)
def test_arrets_par_pilote_degrade_sans_lever(tours):
    """Essais libres, session partielle : ne doit jamais faire échouer la page."""
    assert arrets_par_pilote(tours).empty


def test_resume_arrets_utilise_la_mediane(tours_avec_arrets):
    """Un arrêt anormalement long ne doit pas déformer l'indicateur."""
    arrets = arrets_par_pilote(tours_avec_arrets)

    resume = resume_arrets(arrets)

    assert resume["nombre"] == 3
    assert resume["mediane"] == pytest.approx(2.8)
    assert resume["plus_rapide"] == pytest.approx(2.4)
    assert resume["pilote_plus_rapide"] == "VER"
    assert resume["pilotes"] == 2


def test_resume_arrets_sur_session_sans_arret():
    resume = resume_arrets(pd.DataFrame())

    assert resume["nombre"] == 0
    assert resume["mediane"] is None
    assert resume["plus_rapide"] is None


def test_arrets_par_equipe_classe_du_plus_rapide_au_plus_lent(tours_avec_arrets):
    arrets = arrets_par_pilote(tours_avec_arrets)

    par_equipe = arrets_par_equipe(arrets)

    assert list(par_equipe["Equipe"]) == ["RB", "Mercedes"]
    assert par_equipe["Médiane"].is_monotonic_increasing
    assert int(par_equipe.loc[par_equipe["Equipe"] == "Mercedes", "Arrêts"].iloc[0]) == 2


def test_arrets_par_equipe_sans_colonne_equipe():
    arrets = pd.DataFrame({"Pilote": ["VER"], "Tour": [10], "Duree": [2.5]})

    assert arrets_par_equipe(arrets).empty


# --------------------------------------------------------------------------
# Positions
# --------------------------------------------------------------------------

def test_bilan_positions_calcule_le_solde(tours_course):
    bilan = bilan_positions(tours_course).set_index("Pilote")

    # Position 1 = tête : gagner des places fait baisser le numéro.
    assert bilan.loc["VER", "Solde"] == 2
    assert bilan.loc["HAM", "Solde"] == -1
    assert bilan.loc["NOR", "Solde"] == 0


def test_bilan_positions_trie_par_meilleure_progression(tours_course):
    bilan = bilan_positions(tours_course)

    assert bilan["Pilote"].iloc[0] == "VER"
    assert bilan["Pilote"].iloc[-1] == "HAM"


def test_bilan_positions_retient_la_meilleure_position_atteinte(tours_course):
    bilan = bilan_positions(tours_course).set_index("Pilote")

    assert bilan.loc["HAM", "MeilleurePosition"] == 1
    assert bilan.loc["VER", "MeilleurePosition"] == 1


@pytest.mark.parametrize(
    "tours",
    [
        pd.DataFrame(),
        pd.DataFrame({"Driver": ["VER"], "LapNumber": [1]}),  # pas de Position
        pd.DataFrame({"Driver": ["VER"], "LapNumber": [1], "Position": [float("nan")]}),
    ],
    ids=["vide", "colonne_absente", "positions_absentes"],
)
def test_bilan_positions_degrade_sans_lever(tours):
    """Hors course, OpenF1 ne publie pas les positions."""
    assert bilan_positions(tours).empty


def test_changements_de_position_compte_les_mouvements(tours_course):
    # VER : 3->2->1 (2 changements), HAM : 1->1->2 (1), NOR : stable (0).
    assert changements_de_position(tours_course) == 3


def test_changements_de_position_sur_course_figee():
    figee = pd.DataFrame({
        "Driver": ["VER"] * 3 + ["HAM"] * 3,
        "LapNumber": [1, 2, 3] * 2,
        "Position": [1.0, 1.0, 1.0, 2.0, 2.0, 2.0],
    })

    assert changements_de_position(figee) == 0


def test_changements_de_position_degrade_sans_lever():
    assert changements_de_position(pd.DataFrame()) == 0
    assert changements_de_position(pd.DataFrame({"Driver": ["VER"]})) == 0
