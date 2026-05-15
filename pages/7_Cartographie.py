from src.data import figure_carte_vitesse, figure_carte_rapports, figure_carte_virages
import streamlit as st
from src.config import configure_page
from src.data import chargement_session
from src.ui import selections_courantes, selecteur_pilote_unique
from streamlit_extras.colored_header import colored_header


configure_page("F1 Analytics – Cartographie")
st.subheader("Cartographie")

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


if not pilote:
    st.warning("Sélectionne un pilote dans la barre latérale pour afficher les cartes.")
    st.stop()

colored_header("Carte du circuit", description=None, color_name="blue-70")
# Carte basée sur le tour le plus rapide du pilote sélectionné
fig = figure_carte_virages(sess, pilote=pilote)
st.pyplot(fig, use_container_width=True)

colored_header("Vitesse sur le tour le plus rapide", description=None, color_name="blue-70")
fig = figure_carte_vitesse(sess, pilote=pilote)
st.pyplot(fig, use_container_width=True)

colored_header("Changements de rapport sur le tour le plus rapide", description=None, color_name="blue-70")
fig = figure_carte_rapports(sess, pilote=pilote)
st.pyplot(fig, use_container_width=True)

# Tour 10 de LEC avec traits plus fins
#fig = figure_carte_rapports(sess, pilote="LEC", lap_number=10, linewidth_track=12, linewidth_gears=3)
#st.pyplot(fig)
