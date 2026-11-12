import streamlit as st
from src.session import charger_session_ou_stopper
from src.data import figure_positions_par_tour
from src.ui import selections_courantes, afficher_figure

st.subheader("Performances")
st.caption("*Illustration des changements de positions durant la courses*")
st.warning("*Les résultats ne sont disponibles que pour une session de type : Course (R)*")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = charger_session_ou_stopper(annee, grand_prix, session_type)

fig = figure_positions_par_tour(data["tours"])          # tous les pilotes
# ou : figure_positions_par_tour(data["tours"], pilotes=["VER","HAM","LEC"])

afficher_figure(fig)