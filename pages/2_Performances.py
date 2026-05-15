import streamlit as st
from src.config import configure_page
from src.data import figure_positions_par_tour, chargement_session
from src.ui import selections_courantes

configure_page("F1 Analytics – Performances")

st.subheader("Performances")
st.caption("*Illustration des changements de positions durant la courses*")
st.warning("*Les résultats ne sont disponibles que pour une session de type : Course (R)*")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)
if not loaded:
    st.warning("Aucune session n'est chargée. Retournez à la page d'accueil.")
    st.page_link("Home.py", label="🏠 Retour à la Home")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
sess = data["session"]

fig = figure_positions_par_tour(sess)          # tous les pilotes
# ou : fig = figure_positions_par_tour(sess, pilotes=["VER","HAM","LEC"])

st.pyplot(fig)