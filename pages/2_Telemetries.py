import streamlit as st
import plotly.express as px
from scr.config import configure_page
from scr.ui import selections_courantes, selecteurs_pilotes
from scr.data import chargement_session, tour_rapide_tel
from scr.utils import formatage_timedelta

configure_page("F1 Analytics – Télémétrie")

st.subheader("Télémétrie")
st.caption("Comparaison des performances entre 2 pilotes possible.")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = chargement_session(annee, grand_prix, session_type)
tours = data["tours"]
pilotes = data["pilotes"]


if not loaded:
    st.info("Charge d’abord une session depuis la page Home.")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
tours = data['tours']
pilotes = data['pilotes']

with st.sidebar:
    pilote_1, pilote_2 = selecteurs_pilotes(pilotes)

try:
    d1_fast, tel_1 = tour_rapide_tel(f"{annee}-{grand_prix}-{session_type}", tours, pilote_1)
    fig = px.line(tel_1, x='Distance', y='Speed', title=f"Tour le plus rapide – {pilote_1}")
    if pilote_2:
        d2_fast, tel_2 = tour_rapide_tel(f"{annee}-{grand_prix}-{session_type}", tours, pilote_2)
        fig.add_scatter(x=tel_2['Distance'], y=tel_2['Speed'], mode='lines', name=pilote_2)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.metric(f"Meilleur tour {pilote_1}", formatage_timedelta(d1_fast['LapTime']))
    if pilote_2:
        with c2:
            st.metric(f"Meilleur tour {pilote_2}", formatage_timedelta(d2_fast['LapTime']))
except Exception as e:
    st.info("Télémétrie indisponible pour cette session/pilote.")
    with st.expander("Détails techniques (debug)"):
        st.write(e)