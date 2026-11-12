"""Point d'entrée de l'application — routeur de navigation.

Lancement : `streamlit run streamlit_app.py`

Ce fichier est volontairement mince. Il fait trois choses, dans cet ordre :

1. configure la page et charge le thème (une seule fois pour toute l'app) ;
2. rend le sélecteur de session dans la barre latérale, donc **sur toutes les
   pages** — auparavant il n'existait que sur l'accueil, ce qui obligeait à y
   revenir pour changer de Grand Prix ;
3. délègue à la page sélectionnée.
"""
import streamlit as st

from src.config import configure_page_home
from src.navigation import construire_sections
from src.ui import selecteurs_session_sidebar

configure_page_home(
    "F1 Analytics",
    menu_items={
        "About": (
            "**F1 Analytics** — analyse interactive des week-ends de Formule 1 "
            "à partir des données publiques [OpenF1](https://openf1.org).\n\n"
            "Couverture : saisons 2023 et suivantes."
        ),
        "Report a bug": "https://github.com/Francois-b-24/f1-analytics/issues",
    },
)

# Rendu avant la page : les sélecteurs apparaissent donc en haut de la barre
# latérale, au-dessus des sélecteurs propres à chaque page (pilotes, etc.).
# Le `with st.sidebar` est ici et non dans le fragment : Streamlit interdit à
# une fonction décorée `@st.fragment` d'ouvrir elle-même la barre latérale.
with st.sidebar:
    selecteurs_session_sidebar()

st.navigation(construire_sections()).run()
