import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_extras.colored_header import colored_header

from .openf1 import PREMIERE_SAISON


@st.cache_data(ttl=86400, show_spinner=False)
def _get_event_schedule(annee: int) -> list[str]:
    """Noms des Grands Prix d'une saison, dans l'ordre du calendrier.

    Le cache de 24 h évite de réinterroger OpenF1 à chaque interaction : le
    calendrier d'une saison ne bouge pas.
    """
    from . import openf1
    try:
        return [openf1.nom_grand_prix(c) for c in openf1.courses(annee)]
    except Exception:
        return []


@st.cache_data(ttl=86400, show_spinner=False)
def _last_completed_event(annee: int) -> str | None:
    """Dernier Grand Prix dont la course a déjà eu lieu.

    Évite de pré-sélectionner une épreuve à venir, qui n'aurait aucune donnée.
    Les dates OpenF1 sont tz-aware : la comparaison se fait en UTC.
    """
    from . import openf1
    try:
        courses = openf1.courses(annee)
    except Exception:
        return None
    if not courses:
        return None

    maintenant = pd.Timestamp.utcnow()
    passees = []
    for course in courses:
        date = pd.to_datetime(course.get("date_start"), format="ISO8601",
                              utc=True, errors="coerce")
        if pd.notna(date) and date < maintenant:
            passees.append(course)

    if not passees:
        return None
    return openf1.nom_grand_prix(passees[-1])


def _default_year() -> int:
    """Année par défaut : l'année courante si elle a une course terminée,
    sinon la précédente — jamais avant la première saison couverte."""
    current = datetime.now().year
    if _last_completed_event(current):
        return current
    return max(current - 1, PREMIERE_SAISON)


def selecteurs_session():
    """
    Affiche les sélecteurs de session (année, Grand Prix, type) dans la sidebar.

    Retour
    ------
    tuple
        (année, grand_prix, session_type, loaded)
    """
    default_year = _default_year()
    annee_def = st.session_state.get("annee", default_year)

    events_def = _get_event_schedule(annee_def)
    last_event = _last_completed_event(annee_def) or (events_def[0] if events_def else "")
    grand_prix_def = st.session_state.get("grand_prix", last_event)
    session_type_def = st.session_state.get("session_type", "R")

    # OpenF1, la source de données, ne couvre pas les saisons antérieures à 2023.
    annees = list(range(PREMIERE_SAISON, datetime.now().year + 1))[::-1]
    annee = st.selectbox(
        "Saison", annees,
        index=annees.index(annee_def) if annee_def in annees else 0,
        key="sb_annee",
    )
    events = _get_event_schedule(annee)
    if not events:
        st.warning(f"Calendrier {annee} indisponible (problème réseau ou saison non publiée).")
    grand_prix_options = events if events else ["—"]
    grand_prix = st.selectbox(
        "Grand Prix",
        options=grand_prix_options,
        index=grand_prix_options.index(grand_prix_def) if grand_prix_def in grand_prix_options else 0,
        key="sb_gp",
    )
    session_labels = {
        "FP1": "Essais libres 1",
        "FP2": "Essais libres 2",
        "FP3": "Essais libres 3",
        "Q": "Qualifications",
        "R": "Course",
    }
    session_display = st.selectbox(
        "Type de session",
        list(session_labels.values()),
        index=list(session_labels.keys()).index(session_type_def) if session_type_def in session_labels else 4,
        key="sb_type"
    )
    session_type = [k for k, v in session_labels.items() if v == session_display][0]

    col_load, col_reset = st.columns(2)
    with col_load:
        if st.button("Charger", key="load_btn_home"):
            st.session_state["annee"] = annee
            st.session_state["grand_prix"] = grand_prix
            st.session_state["session_type"] = session_type
            st.session_state["loaded"] = True

    with col_reset:
        if st.button("Réinitialiser", key="reset_btn_home"):
            for key in ["annee", "grand_prix", "session_type", "loaded"]:
                if key in st.session_state:
                    del st.session_state[key]

    return (
        st.session_state.get("annee", annee),
        st.session_state.get("grand_prix", grand_prix),
        st.session_state.get("session_type", session_type),
        st.session_state.get("loaded", False),
    )

def selecteur_pilote_unique(pilotes: list[str]) -> str:
    """
    Affiche un sélecteur pour choisir un seul pilote dans la sidebar.

    Retour
    ------
    str
        Le code du pilote sélectionné, ou "" si aucun pilote disponible.
    """
    colored_header(
        "Pilote",
        description="Choisissez un pilote",
        color_name="blue-70",
    )
    if not pilotes:
        st.caption("Aucun pilote disponible")
        return ""

    default = "HAM" if "HAM" in pilotes else pilotes[0]
    return st.selectbox(
        "Pilote",
        pilotes,
        index=pilotes.index(default),
        key="drv1_sidebar_",
    )

def selecteurs_pilotes(pilotes: list[str]):
    """
    Affiche des sélecteurs pour choisir un ou deux pilotes à comparer.
    
    Paramètres
    ----------
    pilotes : list[str]
        Liste des codes pilotes disponibles.
    
    Retour
    ------
    tuple
        (pilote_1, pilote_2) où pilote_2 peut être une chaîne vide.
    """
    colored_header(
        "Pilotes",
        description="Choisissez un ou deux pilotes à comparer",
        color_name="blue-70",
    )
    # Par défaut, pilote 1 : HAM si dispo
    default1 = "HAM" if "HAM" in pilotes else (pilotes[0] if pilotes else "")
    if pilotes:
        driver_1 = st.selectbox("Pilote 1", pilotes, index=pilotes.index(default1) if default1 in pilotes else 0, key="drv1_sidebar")
        driver_2 = st.selectbox("Pilote 2 (optionnel)", [""] + pilotes, key="drv2_sidebar")
        if driver_2 and driver_2 == driver_1:
            st.warning("Veuillez choisir deux pilotes différents.")
            st.session_state["drv2_sidebar"] = ""
    else:
        st.caption("Aucun pilote disponible")

    d1 = st.session_state.get("drv1_sidebar", default1)
    d2 = st.session_state.get("drv2_sidebar", "") or ""
    if d2 == d1:
        d2 = ""
    return d1, d2

def selections_courantes(required: bool = True):
    """
    Récupère les sélections courantes depuis session_state.
    
    Paramètres
    ----------
    required : bool, optionnel
        Si True, affiche un message et stoppe la page si les données ne sont pas chargées.
    
    Retour
    ------
    tuple
        (année, grand_prix, session_type, loaded)
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

def sidebar_debug_switch():
    """Ajoute un switch dans la sidebar pour activer le mode debug global."""
    with st.sidebar:
        st.session_state['debug_mode'] = st.checkbox('🐞 Mode debug (infos techniques)', value=st.session_state.get('debug_mode', False))

def debug_expander(msg, details):
    """Affiche un expander avec un message et des infos debug si le mode debug est actif."""
    if st.session_state.get('debug_mode', False):
        with st.expander(msg):
            st.write(details)

def context_sidebar_only():
    """Résumé session chargée sans aucune interaction ni selectbox."""
    with st.sidebar:
        st.markdown("""
        <div style='font-size:1.1em;font-weight:bold;margin-bottom:0.5em;'>📋 <u>Session courante :</u></div>""", unsafe_allow_html=True)
        annee = st.session_state.get("annee")
        grand_prix = st.session_state.get("grand_prix")
        session_type = st.session_state.get("session_type")
        loaded = st.session_state.get("loaded")
        if loaded and annee and grand_prix and session_type:
            st.markdown(f"""
            <div style='font-size:0.98em;'><b>🎯 Session:</b> {annee} – {grand_prix} [{session_type}]</div>""", unsafe_allow_html=True)
        else:
            st.error("Aucune session chargée. Revenez à la page Home.")