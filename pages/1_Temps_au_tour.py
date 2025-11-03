import streamlit as st
import plotly.express as px
from scr.config import configure_page
from scr.ui import selecteurs_pilotes, selections_courantes
from scr.data import chargement_session
from scr.utils import formatage_timedelta

configure_page("F1 Analytics – Tours & Chronos")

st.subheader("Tours & Chronos")
st.caption("Comparaison des performances entre 2 pilotes possible.")

# 1) Récupérer les sélections faites sur Home
annee, grand_prix, session_type, loaded = selections_courantes(required=True)

# 2) Charger les données une seule fois (cache côté scr.data)
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

subset = tours[tours['Driver'].isin([d for d in [pilote_1, pilote_2] if d])].copy()

st.subheader("Évolution des temps au tour (en secondes)")
if not subset.empty and subset['LapSeconds'].notna().any():
    fig = px.line(subset, x='LapNumber', y='LapSeconds', color='Driver', labels={'LapSeconds':'Temps (s)'})
    fig.update_xaxes(title_text="Tours")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Données de tours insuffisantes.")

st.subheader("Distribution des temps")
if not subset.empty and subset['LapSeconds'].notna().any():
    fig_h = px.histogram(subset, x='LapSeconds', color='Driver', nbins=30, labels={'LapSeconds':'Temps (s)'}, marginal='box')
    st.plotly_chart(fig_h, use_container_width=True)

st.subheader("Table des tours (filtrable)")
colonnes = ['Driver','LapNumber','LapTime','LapSeconds','Compound','Stint','IsPersonalBest','PitOutTime','PitInTime']
table = subset[[c for c in colonnes if c in subset.columns]].copy()
if 'LapTime' in table:
    table['LapTime'] = table['LapTime'].apply(formatage_timedelta)
if not table.empty:
    st.dataframe(table, use_container_width=True)
    st.download_button(
        "Télécharger CSV",
        data=table.to_csv(index=False).encode('utf-8'),
        file_name=f"laps_{annee}_{grand_prix}_{session_type}.csv",
        mime="text/csv",
    )