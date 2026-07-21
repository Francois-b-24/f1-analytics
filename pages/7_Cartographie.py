from src.data import figure_carte_vitesse, figure_carte_rapports
import streamlit as st
from src.config import configure_page
from src.data import chargement_session
from src.ui import selections_courantes, selecteur_pilote_unique
from streamlit_extras.colored_header import colored_header


configure_page("F1 Analytics – Cartographie")
st.subheader("Cartographie")
st.caption(
    "Tracé du circuit coloré par la vitesse et par le rapport engagé, "
    "sur le tour le plus rapide du pilote sélectionné."
)

annee, grand_prix, session_type, loaded = selections_courantes(required=True)
if not loaded:
    st.warning("Aucune session n'est chargée. Retournez à la page d'accueil.")
    st.page_link("Home.py", label="🏠 Retour à la Home")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
pilotes = data['pilotes']
tel_par_pilote = data.get("tel_par_pilote", {})

with st.sidebar:
    pilote = selecteur_pilote_unique(pilotes)

if not pilote:
    st.warning("Sélectionne un pilote dans la barre latérale pour afficher les cartes.")
    st.stop()

if not tel_par_pilote:
    st.info(
        "⏳ Télémétrie indisponible pour cette session. "
        "Les données sont publiées avec un délai de 24–48 h après la course. "
        "Réessaie plus tard, ou sélectionne une session plus ancienne."
    )
    st.stop()

tel = tel_par_pilote.get(pilote)
if tel is None or tel.empty:
    st.warning(f"Télémétrie non disponible pour {pilote} sur cette session.")
    st.stop()

colored_header("Vitesse sur le tour le plus rapide", description=None, color_name="blue-70")
fig = figure_carte_vitesse(tel)
st.pyplot(fig, use_container_width=True)

colored_header("Changements de rapport sur le tour le plus rapide", description=None, color_name="blue-70")
fig = figure_carte_rapports(tel)
st.pyplot(fig, use_container_width=True)
