import streamlit as st
from scr.config import configure_page
from scr.data import figure_positions_par_tour, chargement_session
from scr.ui import selections_courantes

with open("f1_theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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