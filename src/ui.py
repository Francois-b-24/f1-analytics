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
        _etat_vide()
        st.stop()

    return annee, grand_prix, session_type, loaded

def sidebar_hint_once():
    if "sidebar_hint_ack" not in st.session_state:
        st.session_state["sidebar_hint_ack"] = False
    if not st.session_state["sidebar_hint_ack"]:
        st.caption("Explorez interactivement les données d'un week-end de Grand Prix (tours, télémétrie, pneus, arrêts, météo) ✨")
        st.caption("👈 Astuce : tous les pages sont dans la barre latérale à gauche.")
        st.button("Masquer ce message", on_click=lambda: st.session_state.update(sidebar_hint_ack=True))

def afficher_figure(fig) -> None:
    """Affiche une figure matplotlib puis la libère.

    `st.pyplot` ne ferme pas la figure qu'on lui passe : elle reste référencée
    par le gestionnaire global de matplotlib et n'est jamais collectée.
    Mesuré sur `figure_positions_par_tour`, 30 rendus laissaient 30 figures
    ouvertes et +100 Mo de RSS, contre +20 Mo une fois fermées (et la figure
    construite avec `layout="constrained"`). Sous le plafond de Streamlit
    Cloud (~1 Go), le processus finit par être tué sans trace dans les logs :
    la page semble alors simplement ne plus répondre.
    """
    import matplotlib.pyplot as plt

    st.pyplot(fig, width="stretch")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Préambule de page
#
# Les dix pages répétaient le même bloc : récupérer les sélections, tester
# `loaded`, charger la session. Quatre formulations différentes du même message
# s'étaient installées, et le test `if not loaded` qui suivait
# `selections_courantes(required=True)` était mort — ce dernier appelle déjà
# `st.stop()`. Tout est désormais ici, en un seul endroit.
# ---------------------------------------------------------------------------


def _etat_vide() -> None:
    """Message affiché quand aucune session n'est chargée.

    Formulation unique pour les dix pages. Le lien vers l'accueil passe par
    `lien_accueil()` : sous `st.navigation`, une page est identifiée par son
    objet `StreamlitPage` : lui passer un chemin de fichier lève
    `StreamlitPageNotFoundError` — c'est ce qui avait cassé les dix onglets.

    L'import est différé pour éviter le cycle `ui` ↔ `navigation`.
    """
    st.info(
        "Aucune session chargée. Choisissez une saison, un Grand Prix et un "
        "type de session dans la barre latérale, puis **Charger**."
    )
    from .navigation import lien_accueil

    lien_accueil()


def entete_page(titre: str, icone: str = "", description: str | None = None) -> None:
    """En-tête de page : titre, puis description optionnelle.

    Remplace les `st.subheader` + `st.caption` dispersés, dont la présence et
    la formulation variaient d'une page à l'autre (certaines pages n'avaient
    aucun titre).
    """
    st.title(f"{icone} {titre}".strip())
    if description:
        st.caption(description)


def page_session(titre: str, icone: str = "", description: str | None = None):
    """Préambule commun aux pages : en-tête, sélections, chargement.

    Arrête la page sur un état vide si aucune session n'est chargée — les
    appelants n'ont donc pas à retester `loaded`.

    Retour
    ------
    tuple
        `(data, annee, grand_prix, session_type)` où `data` est le dict
        renvoyé par `chargement_session`.
    """
    from .data import chargement_session

    entete_page(titre, icone, description)
    annee, grand_prix, session_type, _ = selections_courantes(required=True)
    data = chargement_session(annee, grand_prix, session_type)
    return data, annee, grand_prix, session_type
