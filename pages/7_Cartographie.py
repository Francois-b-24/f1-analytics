from src.data import figure_carte_vitesse, figure_carte_rapports
import streamlit as st
from src.config import configure_page
from src.data import telemetrie_pilote
from src.ui import afficher_figure, page_session, selecteur_pilote_unique
from streamlit_extras.colored_header import colored_header


configure_page("F1 Analytics – Cartographie")
data, annee, grand_prix, session_type = page_session(
    "Cartographie", "🗺️",
    "Tracé du circuit coloré par la vitesse et par le rapport engagé, "
    "sur le tour le plus rapide du pilote sélectionné.",
)
pilotes = data['pilotes']
best_laps = data.get("best_laps", {})

with st.sidebar:
    pilote = selecteur_pilote_unique(pilotes)

if not pilote:
    st.warning("Sélectionne un pilote dans la barre latérale pour afficher les cartes.")
    st.stop()

if not best_laps:
    st.info(
        "⏳ Télémétrie indisponible pour cette session. "
        "Les données sont publiées avec un délai de 24–48 h après la course. "
        "Réessaie plus tard, ou sélectionne une session plus ancienne."
    )
    st.stop()

# Télémétrie chargée à la demande, uniquement pour le pilote sélectionné.
with st.spinner(f"Chargement de la télémétrie de {pilote}…"):
    tel = telemetrie_pilote(data, pilote)
if tel is None or tel.empty:
    st.warning(f"Télémétrie non disponible pour {pilote} sur cette session.")
    st.stop()

colored_header("Vitesse sur le tour le plus rapide", description=None, color_name="blue-70")
fig = figure_carte_vitesse(tel)
afficher_figure(fig)

colored_header("Changements de rapport sur le tour le plus rapide", description=None, color_name="blue-70")
fig = figure_carte_rapports(tel)
afficher_figure(fig)
