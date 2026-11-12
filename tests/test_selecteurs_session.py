"""Comportement du sélecteur de session en barre latérale — hors ligne.

Objectif de la phase : changer de Grand Prix depuis n'importe quelle page, sans
repasser par l'accueil. Ces tests exercent ce parcours et figent deux pièges
rencontrés pendant l'implémentation.
"""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

from src.ui import SESSION_LABELS, _index_initial

# Calendriers figés : aucun appel réseau. 2023 n'a pas le GP de 2024, ce qui
# exerce le changement de saison invalidant le Grand Prix sélectionné.
_HARNAIS = '''
import src.ui as ui, streamlit as st
_CAL = {2026: ["GP 2026"], 2025: ["Futur GP"], 2024: ["GP test", "Autre GP"], 2023: ["Vieux GP"]}
ui._get_event_schedule = lambda a: _CAL.get(a, [])
ui._last_completed_event = lambda a: (_CAL.get(a) or [""])[0]
ui._default_year = lambda: 2024
with st.sidebar:
    ui.selecteurs_session_sidebar()
'''


def _app(prelude: str = "") -> AppTest:
    at = AppTest.from_string(prelude + _HARNAIS, default_timeout=60)
    at.run()
    return at


def test_les_trois_selecteurs_sont_dans_la_barre_laterale():
    """C'est le correctif central : ils étaient auparavant dans le corps de l'accueil."""
    at = _app()

    assert [s.label for s in at.sidebar.selectbox] == [
        "Saison", "Grand Prix", "Type de session"
    ]
    assert not at.main.selectbox, "aucun sélecteur de session ne doit rester dans le corps"


def test_charger_valide_la_selection():
    at = _app()
    at.selectbox(key="sb_type").set_value("Qualifications").run()

    # Tant que « Charger » n'est pas cliqué, l'état validé ne bouge pas.
    assert "session_type" not in at.session_state.filtered_state

    at.sidebar.button[0].click().run()

    assert at.session_state["session_type"] == "Q"
    assert at.session_state["loaded"] is True


def test_reinitialiser_efface_la_session():
    at = _app()
    at.sidebar.button[0].click().run()
    assert at.session_state["loaded"] is True

    at.sidebar.button[1].click().run()

    etat = at.session_state.filtered_state
    assert not any(c in etat for c in ("annee", "grand_prix", "session_type", "loaded"))


def test_la_session_active_est_rappelee():
    at = _app()
    at.sidebar.button[0].click().run()

    rappels = [c.value for c in at.sidebar.caption if "Session active" in c.value]
    assert rappels, "l'utilisateur doit voir quelle session il regarde"
    assert "2024" in rappels[0]


def test_une_selection_non_validee_est_signalee():
    """Sans ce repère, on croit regarder un GP qu'on n'a pas chargé."""
    at = _app()
    at.sidebar.button[0].click().run()
    at.selectbox(key="sb_type").set_value("Qualifications").run()

    badges = [m.value for m in at.sidebar.markdown if "Sélection modifiée" in m.value]
    assert badges, "le changement non validé doit être signalé"


def test_changer_de_saison_sans_le_grand_prix_correspondant():
    """2023 ne contient pas le GP sélectionné en 2024 : pas d'exception."""
    at = _app()
    at.selectbox(key="sb_annee").set_value(2023).run()

    assert not at.exception
    assert at.selectbox(key="sb_gp").options == ["Vieux GP"]


def test_calendrier_indisponible_nempeche_pas_le_rendu():
    at = AppTest.from_string(
        '''
import src.ui as ui, streamlit as st
ui._get_event_schedule = lambda a: []
ui._last_completed_event = lambda a: None
ui._default_year = lambda: 2024
with st.sidebar:
    ui.selecteurs_session_sidebar()
''',
        default_timeout=60,
    )
    at.run()

    assert not at.exception
    assert any("indisponible" in w.value for w in at.sidebar.warning)


# --------------------------------------------------------------------------
# Piège figé : couplage index/key
# --------------------------------------------------------------------------

def test_index_initial_ne_sert_quau_premier_rendu():
    """Un selectbox avec `key=` ET un `index=` dérivé de l'état validé boucle.

    Au rerun suivant la validation, l'index serait recalculé depuis l'ancienne
    valeur et écraserait le choix de l'utilisateur : le bouton « Charger »
    paraîtrait sans effet. Une fois le widget créé, `key=` suffit.
    """
    import streamlit as st

    libelles = list(SESSION_LABELS.values())

    # Clé absente : on positionne la valeur par défaut.
    assert _index_initial("absente_du_state", libelles, "Course") == {"index": 4}
    # Valeur inconnue : repli sur la première option plutôt qu'une exception.
    assert _index_initial("absente_du_state", libelles, "Inexistant") == {"index": 0}

    # Clé présente : plus aucun index, sinon le widget régresserait.
    st.session_state["deja_creee"] = "Qualifications"
    try:
        assert _index_initial("deja_creee", libelles, "Course") == {}
    finally:
        del st.session_state["deja_creee"]


def test_aucun_selecteur_de_session_ne_force_son_index():
    """Garde-fou statique : le couplage index/key ne doit pas revenir."""
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "src" / "ui.py").read_text(
        encoding="utf-8"
    )
    debut = source.index("def selecteurs_session_sidebar")
    fin = source.index("def selecteur_pilote_unique")

    assert "index=" not in source[debut:fin], (
        "les sélecteurs de session doivent passer par _index_initial()"
    )
