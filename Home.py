import streamlit as st
from scr.config import configure_page_home
from scr.ui import selecteurs_session, sidebar_hint_once
from scr.data import chargement_session
from scr.utils import formatage_timedelta
import plotly.express as px
import pandas as pd
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space


configure_page_home("F1 Analytics – Home")

st.markdown(
    """
    <div style="text-align:center; font-size: 1.5em; font-weight: 500;">
        <span class="f1-glow"><span class="f1-car-emoji">🏎️</span> F1 Analytics</span>
    </div>
    """,
    unsafe_allow_html=True
)

# Citation Lewis Hamilton
st.markdown(
    '<div class="citation" style="text-align:center;font-size:1.1em;padding-top:0.7em;padding-bottom:0.5em;">'
    '« STILL I RISE » <span style="font-size:0.85em;">– Lewis Hamilton</span>'
    '</div>',
    unsafe_allow_html=True
)


sidebar_hint_once()
# selecteurs_session() gère déjà la persistance dans st.session_state
annee, grand_prix, session_type, loaded = selecteurs_session()


if not loaded:
    st.info("Sélectionnez une année, un Grand Prix et un type de session, puis **Charger**")
    st.stop()

# Chargement du WEEK-END de Grand prix
try:
    _data = chargement_session(annee, grand_prix, session_type)
    session = session_type
    nom_gp = grand_prix
    tours = _data['tours']
    pilotes = _data['pilotes']
    meteo = _data['meteo']
    resultats = _data['resultats']
except Exception as e:
    st.info("Données indisponibles pour cette sélection (connexion, calendrier ou session non disponible).")
    with st.expander("Détails techniques (debug)"):
        st.write(e)
    st.stop()


# Les métriques utilisent maintenant le thème CSS adaptatif

colored_header("Overview", description=None, color_name="blue-70")
# KPIs
c1, c2, c3 = st.columns(3)
total_laps = int(tours['LapNumber'].max()) if not tours.empty else 0
with c1: st.metric("Nombre de tours", f"{total_laps}")
with c2: st.metric("Nombre de pilotes au départ", f"{len(pilotes)}")
with c3: st.metric("Grand-Prix", nom_gp)

add_vertical_space(1)
# Meilleur tour de la session
colored_header("Meilleur tour de la session", description=None, color_name="blue-70")
if 'LapTime' in tours and tours['LapTime'].notna().any():
    best_idx = tours['LapTime'].idxmin()
    best_row = tours.loc[best_idx]
    bcol1, bcol2, bcol3 = st.columns(3)
    with bcol1: st.metric("Pilote", str(best_row.get('Driver', '')))
    with bcol2: st.metric("Tour", int(best_row.get('LapNumber', 0)))
    with bcol3: st.metric("Temps", formatage_timedelta(best_row.get('LapTime')))
else:
    st.info("Meilleur tour indisponible.")


# Top 10 meilleurs tours
colored_header("Chronos — Top 10 meilleurs tours", description=None, color_name="blue-70")
if not tours.empty and 'LapTime' in tours:
    top = (tours.sort_values('LapTime')
                .loc[tours['LapTime'].notna(),
                     ['Driver','LapNumber','LapTime','LapSeconds','Compound','Stint']]
                .head(10))

    top = pd.DataFrame(top).copy()
    top['LapTimeStr'] = top['LapTime'].apply(formatage_timedelta)
    top_display = top[['Driver','LapNumber','LapTimeStr','Compound','Stint']]
    st.dataframe(top_display, use_container_width=True)
else:
    st.info("Pas de données de tours.")

add_vertical_space(1)
# Répartition des pneus
colored_header("Répartition des composés pneus", description=None, color_name="blue-70")
if 'Compound' in tours:
    comp = (tours.dropna(subset=['Compound'])
                .groupby(['Driver','Compound']).size()
                .reset_index(name='Tours'))
    fig = px.bar(comp, x='Driver', y='Tours', color='Compound', barmode='stack')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Pas d'information pneus disponible.")

add_vertical_space(1)
colored_header("Résultats de la course", description="Résultats officiels si disponibles", color_name="blue-70")
if not resultats.empty:
    cols = [c for c in ["Position","BroadcastName","DriverNumber","TeamName","Points","Status","Time","FastestLapTime"] if c in resultats.columns]
    res = resultats[cols].copy()
    res = pd.DataFrame(res).copy()
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
