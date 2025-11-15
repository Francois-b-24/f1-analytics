from scr.data import figure_carte_vitesse, figure_carte_rapports, figure_carte_virages
import streamlit as st
from scr.config import configure_page
from scr.data import chargement_session
from scr.ui import selections_courantes, selecteur_pilote_unique, context_sidebar_only
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.colored_header import colored_header
from streamlit_extras.chart_container import chart_container
from streamlit_extras.add_vertical_space import add_vertical_space

configure_page("F1 Analytics – Cartographie")
st.subheader("Cartographie")

with open("f1_theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

annee, grand_prix, session_type, loaded = selections_courantes(required=True)
if not loaded:
    st.warning("Aucune session n'est chargée. Retournez à la page d'accueil.")
    st.page_link("Home.py", label="🏠 Retour à la Home")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
sess = data["session"]
pilotes = data['pilotes']

with st.sidebar:
    pilote = selecteur_pilote_unique(pilotes)


colored_header("Carte du circuit", description=None, color_name="blue-70")
# Carte simple (tour le plus rapide de la session)
fig = figure_carte_virages(sess)
st.pyplot(fig)

colored_header("Vitesse sur le tour le plus rapide", description=None, color_name="blue-70")
#Exemple 1 : tour le plus rapide de VER
fig = figure_carte_vitesse(sess, pilote=pilote)
st.pyplot(fig)

colored_header("Changements de rapport sur le tour le plus rapide", description=None, color_name="blue-70")
# Tour le plus rapide de VER
fig = figure_carte_rapports(sess, pilote=pilote)
st.pyplot(fig)

# Tour 10 de LEC avec traits plus fins
#fig = figure_carte_rapports(sess, pilote="LEC", lap_number=10, linewidth_track=12, linewidth_gears=3)
#st.pyplot(fig)
