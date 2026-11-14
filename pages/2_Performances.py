import streamlit as st
from src.config import configure_page
from src.data import figure_positions_par_tour
from src.ui import afficher_figure, page_session

configure_page("F1 Analytics – Performances")

data, annee, grand_prix, session_type = page_session(
    "Performances", "📈",
    "Évolution des positions tour après tour.",
)

st.warning(
    "Cette page n'a de sens que pour une session de type **Course (R)** : "
    "les changements de position ne sont pas publiés pour les essais."
)

fig = figure_positions_par_tour(data["tours"])          # tous les pilotes
# ou : figure_positions_par_tour(data["tours"], pilotes=["VER","HAM","LEC"])

afficher_figure(fig)