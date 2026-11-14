import logging
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_extras.colored_header import colored_header

from .openf1 import PREMIERE_SAISON

# Logger obtenu par son nom plutôt qu'importé de `src.config` : ce module y
# tire fastf1 et l'initialisation de Sentry, chaîne d'imports inutile ici et
# qui a fait échouer l'import de `src.ui` en production.
logger = logging.getLogger("f1_analytics.ui")


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


# Libellés des types de session, et seule source de leur ordre d'affichage.
SESSIONS = {
    "FP1": "Essais libres 1",
    "FP2": "Essais libres 2",
    "FP3": "Essais libres 3",
    "Q": "Qualifications",
    "R": "Course",
}


# Auto-chargement de la dernière session terminée au premier affichage.
#
# Sans lui, une page ouverte directement (lien partagé, onglet neuf, favori)
# s'affiche vide : `st.session_state` est propre à chaque session navigateur.
# Avec lui, les onze pages montrent des données d'emblée.
#
# Le coût est réel — sept requêtes OpenF1 et ~3-4 s — d'où trois garde-fous :
# une seule fois par session navigateur, jamais sous test, et un échec qui
# retombe sur l'état vide au lieu de propager une erreur.
#
# Passer cette constante à False restaure le comportement « sélection
# explicite » sans toucher au reste du code.
AUTO_CHARGEMENT = True


def _sous_test() -> bool:
    """Vrai sous pytest, pour qu'aucun test ne déclenche de requête réseau.

    Les tests de rendu vérifient qu'une page n'émet aucun appel OpenF1 : un
    auto-chargement les rendrait faux, et la CI dépendrait du réseau.
    """
    import sys

    return "pytest" in sys.modules or os.environ.get("F1_SANS_AUTO_CHARGEMENT") == "1"


def _auto_charger_si_possible() -> None:
    """Pré-sélectionne et charge la dernière session terminée, une seule fois.

    Ne fait rien si une sélection existe déjà, si l'utilisateur a réinitialisé,
    ou sous test. Les défauts proviennent de `_default_year()` et
    `_last_completed_event()`, qui ne coûtent que le calendrier (caché 24 h) —
    jamais une session.
    """
    if not AUTO_CHARGEMENT or _sous_test():
        return
    if st.session_state.get("auto_charge_tente") or st.session_state.get("loaded"):
        return
    # Un « Réinitialiser » explicite ne doit pas être défait au rerun suivant.
    if st.session_state.get("reinit_demandee"):
        return

    st.session_state["auto_charge_tente"] = True
    try:
        annee = _default_year()
        grand_prix = _last_completed_event(annee)
        if not grand_prix:
            return
        st.session_state.update(
            annee=annee, grand_prix=grand_prix, session_type="R", loaded=True,
        )
    except Exception as exc:  # noqa: BLE001 — un échec ne doit jamais casser la page
        logger.warning("Auto-chargement impossible : %s", exc)


def selecteur_session_global() -> None:
    """Sélecteur de session rendu dans la barre latérale, sur toutes les pages.

    Pourquoi le routeur et pas les pages
    ------------------------------------
    Cette fonction est appelée une seule fois, par `streamlit_app.py`, avant
    `.run()`. Trois conséquences voulues :

    * la sélection est accessible depuis n'importe quelle page — auparavant
      elle ne vivait que sur l'accueil, et changer de Grand Prix imposait d'y
      retourner ;
    * un point de rendu unique rend la duplication de clé structurellement
      impossible. Rendre deux fois la même `key` dans un run lève
      `StreamlitDuplicateElementKey`, une exception non rattrapée qui met la
      page en erreur ;
    * le widget étant rendu avant le corps de la page, une nouvelle sélection
      est déjà lisible quand la page s'exécute, sans second rerun.

    Le bouton **Charger** reste le seul déclencheur de chargement réseau : un
    chargement sur `on_change` partirait à chaque cran de la molette, pour un
    Grand Prix parfois incohérent avec l'année qui vient d'être choisie.
    """
    _auto_charger_si_possible()

    with st.sidebar:
        st.markdown("### Session")

        annee_def = st.session_state.get("annee", _default_year())
        annees = list(range(PREMIERE_SAISON, datetime.now().year + 1))[::-1]
        annee = st.selectbox(
            "Saison", annees,
            index=annees.index(annee_def) if annee_def in annees else 0,
            key="sb_annee",
        )

        events = _get_event_schedule(annee)
        if not events:
            # Discret à dessein : la barre latérale est désormais rendue sur
            # les onze pages, un st.warning y clignoterait partout.
            st.caption(f"⚠️ Calendrier {annee} indisponible (réseau ou saison non publiée).")
        options = events or ["—"]

        gp_def = st.session_state.get("grand_prix") or _last_completed_event(annee) or options[0]
        grand_prix = st.selectbox(
            "Grand Prix", options,
            index=options.index(gp_def) if gp_def in options else 0,
            key="sb_gp",
        )

        type_def = st.session_state.get("session_type", "R")
        libelles = list(SESSIONS.values())
        affiche = st.selectbox(
            "Type de session", libelles,
            index=list(SESSIONS).index(type_def) if type_def in SESSIONS else len(libelles) - 1,
            key="sb_type",
        )
        session_type = next(k for k, v in SESSIONS.items() if v == affiche)

        charger, reinit = st.columns(2)
        with charger:
            if st.button("Charger", key="btn_charger", width="stretch"):
                st.session_state.update(
                    annee=annee, grand_prix=grand_prix,
                    session_type=session_type, loaded=True,
                )
                st.session_state.pop("reinit_demandee", None)
                st.rerun()
        with reinit:
            if st.button("Réinitialiser", key="btn_reinit", width="stretch"):
                for cle in ("annee", "grand_prix", "session_type", "loaded"):
                    st.session_state.pop(cle, None)
                # Mémorisé pour que l'auto-chargement ne rétablisse pas
                # aussitôt la session que l'utilisateur vient d'écarter.
                st.session_state["reinit_demandee"] = True
                st.rerun()

        if st.session_state.get("loaded"):
            st.caption(
                f"Chargée : **{st.session_state['annee']} · "
                f"{st.session_state['grand_prix']} · "
                f"{SESSIONS.get(st.session_state['session_type'], st.session_state['session_type'])}**"
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


def barre_contexte() -> None:
    """Rappelle la session affichée, juste sous le titre de la page.

    Sans ce rappel, rien n'indique à quel Grand Prix se rapportent les
    graphiques : la sélection vit dans la barre latérale, qui peut être
    repliée. Silencieux si aucune session n'est chargée — l'état vide dit déjà
    ce qu'il faut.
    """
    if not st.session_state.get("loaded"):
        return
    annee = st.session_state.get("annee")
    grand_prix = st.session_state.get("grand_prix")
    type_session = st.session_state.get("session_type")
    libelle = SESSIONS.get(type_session, type_session)
    st.markdown(
        '<div class="f1-contexte">'
        f"<span><strong>{annee}</strong></span>"
        '<span class="f1-sep">•</span>'
        f"<span><strong>{grand_prix}</strong></span>"
        '<span class="f1-sep">•</span>'
        f"<span>{libelle}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def entete_page(titre: str, icone: str = "", description: str | None = None) -> None:
    """En-tête de page : titre, description, puis rappel de la session.

    Remplace les `st.subheader` + `st.caption` dispersés, dont la présence et
    la formulation variaient d'une page à l'autre (certaines pages n'avaient
    aucun titre).
    """
    st.title(f"{icone} {titre}".strip())
    if description:
        st.caption(description)
    barre_contexte()


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
