"""Le contrat de `chargement_session` est l'invariant structurant du projet.

Les douze pages consomment ce dict sans savoir d'où viennent les données :
c'est ce qui a permis de migrer de FastF1 vers OpenF1 sans toucher aux pages.
Un test hors ligne garde donc la forme du contrat, là où
`test_data_smoke.py` ne peut le vérifier qu'avec le réseau.

Ces tests exercent aussi les fixtures de `conftest.py`, pour qu'une
divergence entre la session factice et le contrat réel soit détectée.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.adaptateurs import COLONNES_TOURS

# Clés attendues par les pages. Toute disparition est une régression.
CLES_CONTRAT = {
    "nom", "tours", "pilotes", "meteo", "resultats",
    "best_laps", "session_key", "session",
}


def test_la_session_factice_respecte_le_contrat(session_factice):
    assert CLES_CONTRAT.issubset(session_factice)


def test_les_tours_factices_suivent_le_schema_de_production(tours_factices):
    """Les colonnes doivent être celles que `construire_tours` produit.

    Sinon un test passerait sur des données que l'application ne voit jamais.
    """
    attendues = set(COLONNES_TOURS)
    presentes = set(tours_factices.columns)
    manquantes = attendues - presentes

    assert not manquantes, f"colonnes de production absentes de la fixture : {manquantes}"


def test_best_laps_est_un_dict_et_non_un_dataframe(session_factice):
    """Piège vécu : s'en tromper produit un « truth value is ambiguous ».

    Plusieurs pages font `if not best_laps:` — ce qui lève sur un DataFrame.
    """
    best_laps = session_factice["best_laps"]

    assert isinstance(best_laps, dict)
    assert all(isinstance(v, dict) for v in best_laps.values())


def test_pit_in_time_porte_une_duree_pas_un_instant(tours_factices):
    """`PitInTime` vient de `pit_duration` : c'est une durée d'immobilisation.

    Les indicateurs d'arrêts en dépendent (`analytics.arrets_par_pilote`).
    """
    arrets = tours_factices["PitInTime"].dropna()

    assert len(arrets) == 2
    secondes = pd.to_timedelta(arrets).dt.total_seconds()
    # Un arrêt de F1 dure quelques secondes ; un instant de session en ferait
    # des milliers.
    assert secondes.between(1, 60).all(), f"durées suspectes : {list(secondes)}"


@pytest.mark.parametrize(
    "cle,type_attendu",
    [
        ("tours", pd.DataFrame),
        ("meteo", pd.DataFrame),
        ("resultats", pd.DataFrame),
        ("best_laps", dict),
        ("pilotes", list),
        ("nom", str),
    ],
)
def test_les_types_du_contrat(session_factice, cle, type_attendu):
    assert isinstance(session_factice[cle], type_attendu)


def test_la_telemetrie_nest_pas_dans_le_contrat(session_factice):
    """Elle est chargée à la demande, pilote par pilote.

    Charger les 22 pilotes d'emblée coûtait ~45 s alors que la plupart des
    pages n'en affichent aucune.
    """
    assert "telemetrie" not in session_factice
    assert "tel" not in session_factice
