"""Tests du triage d'erreur de chargement — entièrement hors ligne.

Ces tests valident aussi, indirectement, que `charger_session_ou_stopper`
importe `chargement_session` tardivement : si l'import était fait en tête de
module, la substitution opérée par les scripts ci-dessous serait sans effet et
les appels partiraient sur le réseau réel.

Le triage est exercé via `AppTest` et non par un appel direct : hors runtime
Streamlit, `st.stop()` est un no-op (il ne lève qu'en présence d'un contexte de
run) et `st.error()` n'enregistre rien d'observable : tester le helper à nu
reviendrait à vérifier un artefact plutôt que le comportement réel.
"""
from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from src.openf1 import OpenF1Error, OpenF1Indisponible, OpenF1SansDonnees

# Script minimal exerçant le helper dans un vrai runtime. AppTest exécute le
# script dans son propre module : la substitution de chargement_session est
# donc faite depuis l'intérieur du script, avant l'appel au helper.
_SCRIPT = """
import src.data
src.data.chargement_session = {fabrique}

from src.session import charger_session_ou_stopper
data = charger_session_ou_stopper(2024, "Australia Grand Prix (Melbourne)", "R")

import streamlit as st
st.title("Chargement réussi")
st.metric("Tours", len(data["tours"]))
"""


def _lancer(fabrique: str) -> AppTest:
    at = AppTest.from_string(_SCRIPT.format(fabrique=fabrique), default_timeout=30)
    at.run()
    return at


def test_retourne_le_dict_en_cas_de_succes():
    at = _lancer('lambda *a, **k: {"tours": __import__("pandas").DataFrame({"L": [1, 2]})}')

    assert not at.exception
    assert at.title[0].value == "Chargement réussi"
    assert at.metric[0].value == "2"
    assert not at.error


@pytest.mark.parametrize(
    ("fabrique", "attendu"),
    [
        (
            '(lambda *a, **k: (_ for _ in ()).throw('
            '__import__("src.openf1", fromlist=["x"]).OpenF1SansDonnees("introuvable")))',
            "pas encore eu lieu",
        ),
        (
            '(lambda *a, **k: (_ for _ in ()).throw('
            '__import__("src.openf1", fromlist=["x"]).OpenF1Indisponible("URLError")))',
            "injoignable",
        ),
        (
            '(lambda *a, **k: (_ for _ in ()).throw(ValueError("panne inattendue")))',
            "ValueError",
        ),
    ],
    ids=["sans_donnees", "indisponible", "inattendue"],
)
def test_affiche_un_message_cible_et_arrete_la_page(fabrique, attendu):
    """Chaque type de panne produit son propre message, et la page s'arrête."""
    at = _lancer(fabrique)

    # Pas de traceback brute remontée à l'utilisateur.
    assert not at.exception
    # Un message d'erreur ciblé a été rendu.
    assert at.error, "aucun st.error rendu"
    assert attendu in at.error[0].value
    # st.stop() a bien coupé : le titre qui suit l'appel n'est jamais rendu.
    assert not at.title


def test_reessayer_absent_quand_reessayer_est_inutile():
    """Sur absence de données publiées, réessayer ne changerait rien."""
    at = _lancer(
        '(lambda *a, **k: (_ for _ in ()).throw('
        '__import__("src.openf1", fromlist=["x"]).OpenF1SansDonnees("introuvable")))'
    )

    assert not any(b.label == "🔄 Réessayer" for b in at.button)


def test_reessayer_present_quand_api_injoignable():
    """Sur panne réseau, l'utilisateur doit pouvoir relancer."""
    at = _lancer(
        '(lambda *a, **k: (_ for _ in ()).throw('
        '__import__("src.openf1", fromlist=["x"]).OpenF1Indisponible("URLError")))'
    )

    assert any(b.label == "🔄 Réessayer" for b in at.button)


def test_les_sous_classes_restent_rattrapables_comme_avant():
    """Un `except OpenF1Error` existant doit continuer de fonctionner.

    C'est la mitigation du risque de la phase 1 : on a changé les types levés,
    pas la hiérarchie à laquelle ils appartiennent.
    """
    assert issubclass(OpenF1Indisponible, OpenF1Error)
    assert issubclass(OpenF1SansDonnees, OpenF1Error)
    assert issubclass(OpenF1Error, RuntimeError)
