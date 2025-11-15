import streamlit as st
import fastf1
from datetime import datetime
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.metric_cards import style_metric_cards

# Mapping des logos équipe F1 (2024, adapter selon disponibilités logos)
F1_TEAM_LOGOS = {
    "Red Bull": "https://upload.wikimedia.org/wikipedia/en/thumb/8/8b/Red_Bull_Racing_logo.svg/220px-Red_Bull_Racing_logo.svg.png",
    "Mercedes": "https://upload.wikimedia.org/wikipedia/en/thumb/a/af/Mercedes-Benz_in_Motorsport_logo.svg/220px-Mercedes-Benz_in_Motorsport_logo.svg.png",
    "Ferrari": "https://upload.wikimedia.org/wikipedia/en/thumb/3/3d/Scuderia_Ferrari_Logo.svg/180px-Scuderia_Ferrari_Logo.svg.png",
    "McLaren": "https://upload.wikimedia.org/wikipedia/en/thumb/6/6f/McLaren_Racing_logo.svg/180px-McLaren_Racing_logo.svg.png",
    "Aston Martin": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Aston_Martin_Racing_logo.svg/190px-Aston_Martin_Racing_logo.svg.png",
    "Alpine": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/BWT_Alpine_F1_Team_logo.svg/220px-BWT_Alpine_F1_Team_logo.svg.png",
    "Williams": "https://upload.wikimedia.org/wikipedia/en/thumb/6/6a/Williams_Grand_Prix_Engineering_logo.svg/220px-Williams_Grand_Prix_Engineering_logo.svg.png",
    "Haas": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Haas_F1_Team_logo.svg/190px-Haas_F1_Team_logo.svg.png",
    "RB": "https://upload.wikimedia.org/wikipedia/commons/4/46/RB_F1_Team_logo_2024.png",
    "Sauber": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Kick_Sauber_F1_Team_logo_2024.png/220px-Kick_Sauber_F1_Team_logo_2024.png",
}

F1_DRIVER_IMAGES = {
    "HAM": "https://upload.wikimedia.org/wikipedia/commons/8/87/Lewis_Hamilton_Mercedes_AMG_Petronas_F1_Team_2023_%28cropped%29.jpg",
    "VER": "https://upload.wikimedia.org/wikipedia/commons/8/83/Max_Verstappen_2023.png",
    "LEC": "https://upload.wikimedia.org/wikipedia/commons/2/2d/Charles_Leclerc_Ferrari_F1_2022.jpg",
    "NOR": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Lando_Norris_McLaren_2022.jpg",
}

def render_team_logo(team_name, height=18):
    url = F1_TEAM_LOGOS.get(team_name)
    if not url:
        return team_name
    return f'<img src="{url}" height="{height}" style="vertical-align:middle;margin-right:0.5em;"> {team_name}'

def render_driver_img(code, name, height=20):
    url = F1_DRIVER_IMAGES.get(code)
    if not url:
        return name
    return f'<img src="{url}" height="{height}" style="vertical-align:middle;border-radius:12px;"> {name}'

def selecteurs_session():
    import streamlit as st
    from streamlit_extras.colored_header import colored_header
    import fastf1
    from datetime import datetime

    colored_header(
        "Session",
        description="Sélectionnez la saison, le Grand Prix et le type de session",
        color_name="blue-70",
    )

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
    """Récupère (annee, grand_prix, session_type, loaded, pilote 1 et 2) depuis session_state.
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