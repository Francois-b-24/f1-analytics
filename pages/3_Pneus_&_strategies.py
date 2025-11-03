import streamlit as st
import plotly.express as px
from scr.config import configure_page
from scr.ui import selections_courantes
from scr.data import chargement_session

configure_page("F1 Analytics – Pneus & Stratégie")

st.subheader("Pneus & Stratégie")


annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = chargement_session(annee, grand_prix, session_type)
tours = data["tours"]
pilotes = data["pilotes"]

if not loaded:
    st.info("Charge d’abord une session depuis la page Home.")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
tours = data['tours']

st.subheader("Stints par pilote")
if {'Stint','Compound','LapNumber'}.issubset(tours.columns):
    stint_ranges = (tours.dropna(subset=['Stint'])
                        .groupby(['Driver','Stint'])
                        .agg(StartLap=('LapNumber','min'), EndLap=('LapNumber','max'),
                             Compound=('Compound', 'last'))
                        .reset_index())
    st.dataframe(stint_ranges, use_container_width=True)

    st.subheader("Performance moyenne par stint (temps moyen)")
    perf = (tours.dropna(subset=['LapSeconds','Stint'])
                .groupby(['Driver','Stint','Compound'])['LapSeconds']
                .mean().reset_index(name='AvgLapSec'))
    fig = px.bar(perf, x='Driver', y='AvgLapSec', color='Compound', barmode='group', facet_row='Stint',
                 labels={'AvgLapSec':'Temps moyen (s)'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Les informations de stints/pneus ne sont pas disponibles pour cette session.")