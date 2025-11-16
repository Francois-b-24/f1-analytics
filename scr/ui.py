import streamlit as st
from streamlit_extras.colored_header import colored_header

def selecteurs_session():
    """
    Affiche les sélecteurs de session (année, Grand Prix, type) dans la sidebar.
    
    Retour
    ------
    tuple
        (année, grand_prix, session_type, loaded)
    """
    import fastf1
    from datetime import datetime
    from streamlit_extras.colored_header import colored_header

    # Préremplir avec dernier choix stocké si dispo, sinon valeurs par défaut
    annee_def = st.session_state.get("annee", datetime.now().year)
    try:
        schedule = fastf1.get_event_schedule(annee_def, include_testing=False)
        events = schedule['EventName'].tolist()
    except Exception:
        events = []
    grand_prix_def = st.session_state.get("grand_prix", events[0] if events else "")
    session_type_def = st.session_state.get("session_type", "R")

    annee = st.selectbox("Saison", list(range(2018, datetime.now().year + 1))[::-1], index=list(range(2018, datetime.now().year + 1))[::-1].index(annee_def), key="sb_annee")
    try:
        schedule = fastf1.get_event_schedule(annee, include_testing=False)
        events = schedule['EventName'].tolist()
    except Exception:
        events = []
    grand_prix = st.selectbox("Grand Prix", options=events if events else ["Bahrain", "Monaco", "Monza"], index=events.index(grand_prix_def) if grand_prix_def in events else 0, key="sb_gp")
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

def selecteur_pilote_unique(pilotes: list[str]):
    """
    Affiche un sélecteur pour choisir un seul pilote dans la sidebar.
    
    Paramètres
    ----------
    pilotes : list[str]
        Liste des codes pilotes disponibles (ex: ["HAM", "VER", "LEC"]).
    
    Retour
    ------
    str
        Le code du pilote sélectionné (par défaut "HAM" si disponible).
    """
    colored_header(
        "Pilotes",
        description="Choisissez un pilotes",
        color_name="blue-70",
    )
    # Par défaut, HAM si dispo sinon premier pilote
    default = "HAM" if "HAM" in pilotes else (pilotes[0] if pilotes else "")
    if pilotes:
        st.selectbox("Pilote", pilotes, index=pilotes.index(default) if default in pilotes else 0, key="drv1_sidebar_")
    else:
        st.caption("Aucun pilote disponible")

    d1 = st.session_state.get("drv1_sidebar_", default)
    if d1 == "" :
        d1 = ""
    return d1

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