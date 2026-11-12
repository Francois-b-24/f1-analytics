"""Les points d'entrée doivent démarrer — hors ligne.

Régression vécue : renommer `Home.py` en `streamlit_app.py` a cassé la
production avec « Error running app », alors que lint, tests et CI étaient
verts. La configuration « Main file path » de Streamlit Cloud vit **hors du
dépôt** : rien dans le projet ne signalait qu'un fichier attendu avait disparu.

Ces tests vérifient donc que chaque point d'entrée supporté démarre réellement,
et non seulement qu'il s'importe.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

RACINE = Path(__file__).resolve().parent.parent

# Fichiers que Streamlit Cloud peut avoir configurés comme point d'entrée.
# `Home.py` est conservé parce que l'app déployée le référence encore.
POINTS_ENTREE = ["streamlit_app.py", "Home.py"]


@pytest.mark.parametrize("fichier", POINTS_ENTREE)
def test_le_point_dentree_existe(fichier):
    assert (RACINE / fichier).is_file(), (
        f"{fichier} est absent : si Streamlit Cloud le référence comme "
        "« Main file path », l'app ne démarrera pas"
    )


@pytest.mark.parametrize("fichier", POINTS_ENTREE)
def test_le_point_dentree_demarre_sans_exception(fichier):
    """Un import réussi ne suffit pas : c'est le rendu qui échouait."""
    at = AppTest.from_file(str(RACINE / fichier), default_timeout=60)
    at.run()

    assert not at.exception, [e.value for e in at.exception]


@pytest.mark.parametrize("fichier", POINTS_ENTREE)
def test_le_point_dentree_rend_le_selecteur_de_session(fichier):
    """Les deux points d'entrée doivent produire la même application."""
    at = AppTest.from_file(str(RACINE / fichier), default_timeout=60)
    at.run()

    assert [s.label for s in at.sidebar.selectbox] == [
        "Saison", "Grand Prix", "Type de session"
    ]


def test_les_pages_sont_resolues_depuis_la_racine_du_projet():
    """`st.Page` résout un chemin relatif depuis le script d'entrée.

    Des chemins relatifs rendraient le registre dépendant du répertoire du
    script lancé — un point d'entrée placé ailleurs ne trouverait plus les
    pages (« Unable to create Page »).
    """
    source = (RACINE / "src" / "navigation.py").read_text(encoding="utf-8")

    assert "_RACINE" in source
    assert 'st.Page(\n                _RACINE / entree["fichier"]' in source or (
        "_RACINE / entree" in source
    ), "les chemins de pages doivent être ancrés sur la racine du projet"
