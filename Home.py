import streamlit as st
from scr.config import configure_page_home
from scr.ui import selecteurs_session, selecteurs_pilotes, sidebar_hint_once
from scr.data import chargement_session
from scr.utils import formatage_timedelta
import plotly.express as px

configure_page_home("F1 Analytics – Home")


st.title("🏎️ F1 Analytics")
sidebar_hint_once()
annee, grand_prix, session_type, loaded = selecteurs_session()
st.session_state["annee"] = annee
st.session_state["grand_prix"] = grand_prix
st.session_state["session_type"] = session_type
st.session_state["loaded"] = loaded

if not loaded:
    st.info("Sélectionnez une saison, un Grand Prix et un type de session, puis cliquez **Charger** les données et parcourez les pages.")
    st.stop()

# Chargement du WEEK-END de Grand prix
try:
    data = chargement_session(annee, grand_prix, session_type)
    nom_gp = data['nom']
    tours = data['tours']
    pilotes = data['pilotes']
    meteo = data['meteo']
    resultats = data['resultats']
    st.success(f"Session {nom_gp} chargée ✅")
except Exception as e:
    st.info("Données indisponibles pour cette sélection (connexion, calendrier ou session non disponible).")
    with st.expander("Détails techniques (debug)"):
        st.write(e)
    st.stop()

with st.sidebar:
    d1, d2 = selecteurs_pilotes(pilotes)

# KPIs
c1, c2, c3, c4 = st.columns(4)
total_laps = int(tours['LapNumber'].max()) if not tours.empty else 0
with c1: st.metric("Nombre de tours", f"{total_laps}")
with c2: st.metric("Nombre de pilotes au départ", f"{len(pilotes)}")
with c3: st.metric("Session", session_type)
with c4: st.metric("Grand-Prix", nom_gp)

# Top 10 meilleurs tours
st.subheader("Chronos – Top 10 meilleurs tours de la session")
if not tours.empty and 'LapTime' in tours:
    top = (tours.sort_values('LapTime')
                .loc[tours['LapTime'].notna(),
                     ['Driver','LapNumber','LapTime','LapSeconds','Compound','Stint']]
                .head(10))
    top['LapTimeStr'] = top['LapTime'].apply(formatage_timedelta)
    st.dataframe(top[['Driver','LapNumber','LapTimeStr','Compound','Stint']], use_container_width=True)
else:
    st.info("Pas de données de tours.")

# Répartition des pneus
st.subheader("Répartition des composés pneus")
if 'Compound' in tours:
    comp = (tours.dropna(subset=['Compound'])
                .groupby(['Driver','Compound']).size()
                .reset_index(name='Tours'))
    fig = px.bar(comp, x='Driver', y='Tours', color='Compound', barmode='stack')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Pas d'information pneus disponible.")

# Résultats de course (si disponibles)
st.subheader("Résultats de la course")
if not resultats.empty:
    cols = [c for c in ["Position","Abbreviation","DriverNumber","TeamName","Points","Status","Time","FastestLapTime"] if c in resultats.columns]
    res = resultats[cols].copy()
    for c in ["Time","FastestLapTime"]:
        if c in res.columns:
            try:
                res[c] = res[c].apply(formatage_timedelta)
            except Exception:
                pass
    st.markdown("Résultats officiels **(si disponibles)**")
    st.dataframe(res, use_container_width=True)
else:
    st.info("Résultats non disponibles pour cette session.")

# Meilleur tour de la session
st.subheader("Meilleur tour de la session")
if 'LapTime' in tours and tours['LapTime'].notna().any():
    best_idx = tours['LapTime'].idxmin()
    best_row = tours.loc[best_idx]
    bcol1, bcol2, bcol3 = st.columns(3)
    with bcol1: st.metric("Pilote", str(best_row.get('Driver', '')))
    with bcol2: st.metric("Tour", int(best_row.get('LapNumber', 0)))
    with bcol3: st.metric("Temps", formatage_timedelta(best_row.get('LapTime')))
else:
    st.info("Meilleur tour indisponible.")