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


def _index_initial(cle: str, options: list, valeur) -> dict:
    """Arguments d'index à passer à un selectbox, seulement au premier rendu.

    Piège : un selectbox qui reçoit à la fois `key=` et un `index=` dérivé de
    l'état validé boucle sur lui-même. Au rerun déclenché par « Charger »,
    l'index est recalculé depuis l'**ancienne** valeur et écrase le choix que
    l'utilisateur vient de faire — le widget revient en arrière et la
    validation paraît sans effet.

    Une fois le widget créé, `key=` assure seule la persistance : on ne fournit
    donc `index` que tant que la clé est absente de `session_state`.
    """
    if cle in st.session_state:
        return {}
    try:
        return {"index": options.index(valeur)}
    except ValueError:
        return {"index": 0}


SESSION_LABELS = {
    "FP1": "Essais libres 1",
    "FP2": "Essais libres 2",
    "FP3": "Essais libres 3",
    "Q": "Qualifications",
    "R": "Course",
}


@st.fragment
def selecteurs_session_sidebar() -> None:
    """Rend le sélecteur de session dans la barre latérale, sur toutes les pages.

    Rendu par le routeur (`streamlit_app.py`), donc disponible partout : avant,
    les sélecteurs n'existaient que sur l'accueil et changer de Grand Prix
    depuis une page imposait d'y retourner.

    Le bouton « Charger » est conservé **à dessein** plutôt qu'un chargement
    automatique au changement de sélection. Deux raisons :

    - le cache de session est plafonné à 2 entrées pour tenir dans la limite
      mémoire de Streamlit Cloud ; parcourir trois saisons en auto-chargement
      déclencherait trois chargements réseau dont deux aussitôt évincés ;
    - changer de saison invalide le Grand Prix sélectionné, et un chargement
      automatique partirait sur un couple (saison, GP) incohérent.

    Le fragment évite que changer de saison — qui recharge le calendrier — ne
    relance le rendu de la page entière. Aucun `st.stop()` ici : dans un
    fragment, il n'arrêterait que le fragment.

    À appeler **dans** un `with st.sidebar:` : Streamlit interdit à un fragment
    d'ouvrir lui-même la barre latérale.
    """
    st.markdown("### Session")

    annee_def = st.session_state.get("annee", _default_year())
    events_def = _get_event_schedule(annee_def)
    last_event = _last_completed_event(annee_def) or (events_def[0] if events_def else "")
    grand_prix_def = st.session_state.get("grand_prix", last_event)
    session_type_def = st.session_state.get("session_type", "R")

    # OpenF1 ne couvre pas les saisons antérieures à 2023.
    annees = list(range(PREMIERE_SAISON, datetime.now().year + 1))[::-1]
    annee = st.selectbox(
        "Saison", annees,
        key="sb_annee",
        **_index_initial("sb_annee", annees, annee_def),
    )

    events = _get_event_schedule(annee)
    if not events:
        st.warning(
            f"Calendrier {annee} indisponible "
            "(problème réseau ou saison non publiée)."
        )
    grand_prix_options = events if events else ["—"]
    grand_prix = st.selectbox(
        "Grand Prix",
        options=grand_prix_options,
        key="sb_gp",
        **_index_initial("sb_gp", grand_prix_options, grand_prix_def),
    )

    libelles = list(SESSION_LABELS.values())
    session_display = st.selectbox(
        "Type de session",
        libelles,
        key="sb_type",
        **_index_initial("sb_type", libelles, SESSION_LABELS.get(session_type_def)),
    )
    session_type = [k for k, v in SESSION_LABELS.items() if v == session_display][0]

    # La sélection des widgets peut différer de la session réellement
    # chargée : le signaler évite de croire qu'on regarde un autre GP.
    charge = st.session_state.get("loaded", False)
    modifiee = charge and (
        annee != st.session_state.get("annee")
        or grand_prix != st.session_state.get("grand_prix")
        or session_type != st.session_state.get("session_type")
    )

    if modifiee:
        st.badge("Sélection modifiée", color="orange")

    col_charger, col_reset = st.columns(2)
    with col_charger:
        if st.button(
            "Charger",
            key="btn_charger_session",
            type="primary" if (modifiee or not charge) else "secondary",
            width="stretch",
        ):
            st.session_state["annee"] = annee
            st.session_state["grand_prix"] = grand_prix
            st.session_state["session_type"] = session_type
            st.session_state["loaded"] = True
            # `scope="app"` est indispensable : par défaut, un `st.rerun()`
            # appelé dans un fragment ne relance que le fragment, et la page
            # continuerait d'afficher la session précédente.
            st.rerun(scope="app")

    with col_reset:
        if st.button("Réinitialiser", key="btn_reset_session", width="stretch"):
            for cle in ("annee", "grand_prix", "session_type", "loaded"):
                st.session_state.pop(cle, None)
            st.rerun(scope="app")

    if charge and not modifiee:
        st.caption(
            f"Session active : **{st.session_state['annee']}** · "
            f"{st.session_state['grand_prix']} · "
            f"{SESSION_LABELS.get(st.session_state['session_type'], '?')}"
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
        # Les sélecteurs sont dans la barre latérale, sur cette page : plus
        # besoin de renvoyer l'utilisateur vers l'accueil.
        st.info(
            "👈 Choisissez une saison, un Grand Prix et un type de session "
            "dans la barre latérale, puis cliquez sur **Charger**."
        )
        st.stop()

    return annee, grand_prix, session_type, loaded

def sidebar_hint_once():
    """Pitch de l'app, masquable — affiché sur l'accueil uniquement."""
    if st.session_state.get("sidebar_hint_ack"):
        return
    st.caption(
        "Explorez les données d'un week-end de Grand Prix : tours, télémétrie, "
        "pneus, arrêts, météo ✨"
    )
    st.caption("👈 Les pages sont regroupées par thème dans la barre latérale.")
    st.button(
        "Masquer ce message",
        on_click=lambda: st.session_state.update(sidebar_hint_ack=True),
    )

def afficher_figure(fig) -> None:
    """Affiche une figure matplotlib puis la libère.

    `st.pyplot` ne ferme pas la figure : sans `plt.close`, chaque rerun en
    accumule une de plus dans le gestionnaire global de matplotlib. Sous le
    plafond mémoire de Streamlit Cloud (~1 Go), les pages à cartes de circuit
    finissaient par faire tuer le processus.
    """
    import matplotlib.pyplot as plt

    st.pyplot(fig, width="stretch")
    plt.close(fig)
