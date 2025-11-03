import streamlit as st
import fastf1
from datetime import datetime

def selecteurs_session():
    st.header("Session")

    annee = st.selectbox("Saison", list(range(2018, datetime.now().year + 1))[::-1])

    try:
        schedule = fastf1.get_event_schedule(annee, include_testing=False)
        events = schedule['EventName'].tolist()
    except Exception:
        events = []
    event_name = st.selectbox("Grand Prix", options=events if events else ["Bahrain", "Monaco", "Monza"])
    session_type = st.selectbox("Type de session", ["FP1", "FP2", "FP3", "Q", "R"])

    if "loaded" not in st.session_state:
        st.session_state["loaded"] = False

    col_load, col_reset = st.columns(2)
    with col_load:
        st.button("Charger", key="load_btn", on_click=lambda: st.session_state.update(loaded=True))
    with col_reset:
        st.button("Réinitialiser", key="reset_btn", on_click=lambda: st.session_state.update(loaded=False))

    return annee, event_name, session_type, st.session_state.get("loaded", False)

def selecteurs_pilotes(pilotes: list[str]):
    st.subheader("Pilotes")
    if pilotes:
        driver_1 = st.selectbox("Pilote 1", pilotes, key="drv1_sidebar")
        driver_2 = st.selectbox("Pilote 2 (optionnel)", [""] + pilotes, key="drv2_sidebar")
        if driver_2 and driver_2 == driver_1:
            st.warning("Veuillez choisir deux pilotes différents.")
            st.session_state["drv2_sidebar"] = ""
    else:
        st.caption("Aucun pilote disponible")

    d1 = st.session_state.get("drv1_sidebar", pilotes[0] if pilotes else "")
    d2 = st.session_state.get("drv2_sidebar", "") or ""
    if d2 == d1:
        d2 = ""
    return d1, d2

import streamlit as st

def selections_courantes(required: bool = True):
    """Récupère (annee, grand_prix, session_type, loaded) depuis session_state.
    Si required=True et que ce n'est pas prêt, affiche un message et stoppe la page.
    """
    annee = st.session_state.get("annee")
    grand_prix = st.session_state.get("grand_prix")
    session_type = st.session_state.get("session_type")
    loaded = st.session_state.get("loaded", False)

    if required and (annee is None or grand_prix is None or session_type is None or not loaded):
        st.info("Veuillez d’abord sélectionner et **charger** une session sur la page **Home**.")
        st.page_link("Home.py", label="🏠 Aller à la page Home")
        st.stop()

    return annee, grand_prix, session_type, loaded

def sidebar_hint_once():
    if "sidebar_hint_ack" not in st.session_state:
        st.session_state["sidebar_hint_ack"] = False
    if not st.session_state["sidebar_hint_ack"]:
        st.caption("Explorez interactivement les données d'un week-end de Grand Prix (tours, télémétrie, pneus, arrêts, météo) ✨")
        st.caption("👈 Astuce : tous les pages sont dans la barre latérale à gauche.")
        st.button("Masquer ce message", on_click=lambda: st.session_state.update(sidebar_hint_ack=True))