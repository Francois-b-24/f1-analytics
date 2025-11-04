import streamlit as st
from scr.config import configure_page_home
from scr.ui import selecteurs_session, selecteurs_pilotes, sidebar_hint_once
from scr.data import chargement_session
from scr.utils import formatage_timedelta
import plotly.express as px
import pandas as pd
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.colored_header import colored_header
from streamlit_extras.chart_container import chart_container
from streamlit_extras.add_vertical_space import add_vertical_space

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
    _data = chargement_session(annee, grand_prix, session_type)
    nom_gp = _data['nom']
    tours = _data['tours']
    pilotes = _data['pilotes']
    meteo = _data['meteo']
    resultats = _data['resultats']
    st.success(f"Session {nom_gp} chargée ✅")
except Exception as e:
    st.info("Données indisponibles pour cette sélection (connexion, calendrier ou session non disponible).")
    with st.expander("Détails techniques (debug)"):
        st.write(e)
    st.stop()

with st.sidebar:
    d1, d2 = selecteurs_pilotes(pilotes)

style_metric_cards(background_color = "#FFFFFF", border_color="#2B313E", border_left_color="#00D4FF", border_radius_px=8, box_shadow=True)

st.markdown(
    """
<style>
/* Robust theming for Streamlit metrics: handles macOS/browsers dark mode and Streamlit's own theme attr */

/* System preference (browser) */
@media (prefers-color-scheme: light) {
  div[data-testid="stMetric"] {
    background-color: #FFFFFF !important;
    border: 1px solid #2B313E !important;
    border-left: 0.5rem solid #00D4FF !important;
    border-radius: 8px !important;
    padding: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
  }
  div[data-testid="stMetric"] * { color: #000000 !important; }
}

@media (prefers-color-scheme: dark) {
  div[data-testid="stMetric"] {
    background-color: #2B313E !important;
    border: 1px solid #00D4FF !important;
    border-left: 0.5rem solid #00D4FF !important;
    border-radius: 8px !important;
    padding: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
  }
  div[data-testid="stMetric"] * { color: #FFFFFF !important; }
}

/* Streamlit theme attribute overrides (higher priority than media query on some setups) */
html[data-theme="light"] div[data-testid="stMetric"],
body[data-theme="light"] div[data-testid="stMetric"] {
  background-color: #FFFFFF !important;
  border: 1px solid #2B313E !important;
  border-left: 0.5rem solid #00D4FF !important;
}
html[data-theme="light"] div[data-testid="stMetric"] *,
body[data-theme="light"] div[data-testid="stMetric"] * { color: #000000 !important; }

html[data-theme="dark"] div[data-testid="stMetric"],
body[data-theme="dark"] div[data-testid="stMetric"] {
  background-color: #2B313E !important;
  border: 1px solid #00D4FF !important;
  border-left: 0.5rem solid #00D4FF !important;
}
html[data-theme="dark"] div[data-testid="stMetric"] *,
body[data-theme="dark"] div[data-testid="stMetric"] * { color: #FFFFFF !important; }

/* Explicit targets for value/label to win against Streamlit inline styles */
span[data-testid="stMetricValue"],
div[data-testid="stMetricLabel"] { color: inherit !important; font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)

colored_header("Overview", description=None, color_name="blue-70")
# KPIs
c1, c2, c3, c4 = st.columns(4)
total_laps = int(tours['LapNumber'].max()) if not tours.empty else 0
with c1: st.metric("Nombre de tours", f"{total_laps}")
with c2: st.metric("Nombre de pilotes au départ", f"{len(pilotes)}")
with c3: st.metric("Session", session_type)
with c4: st.metric("Grand-Prix", nom_gp)

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
    with chart_container(comp):
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Pas d'information pneus disponible.")

add_vertical_space(1)
colored_header("Résultats de la course", description="Résultats officiels si disponibles", color_name="blue-70")
if not resultats.empty:
    cols = [c for c in ["Position","Abbreviation","DriverNumber","TeamName","Points","Status","Time","FastestLapTime"] if c in resultats.columns]
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
