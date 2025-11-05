import streamlit as st
import plotly.express as px
from scr.config import configure_page
from scr.ui import selecteurs_pilotes, selections_courantes
from scr.data import chargement_session, tour_rapide_tel
from scr.utils import formatage_timedelta
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.colored_header import colored_header
from streamlit_extras.chart_container import chart_container
from streamlit_extras.add_vertical_space import add_vertical_space

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

colored_header("Évolution des temps au tour (en secondes)", description=None, color_name="blue-70")
if not subset.empty and subset['LapSeconds'].notna().any():
    fig = px.line(subset, x='LapNumber', y='LapSeconds', color='Driver', labels={'LapSeconds':'Temps (s)'})
    fig.update_xaxes(title_text="Tours")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Données de tours insuffisantes.")

def _get_best_lap_no(d):
    """Retourne le numéro du tour du meilleur tour depuis d1_fast/d2_fast."""
    try:
        for key in ("LapNumber", "Lap", "BestLapNo", "BestLap"):
            try:
                val = d.get(key)
            except Exception:
                val = d[key] if key in d else None
            if val is not None:
                return int(val)
    except Exception:
        pass
    return None

colored_header("Télémétries sur le tour le plus rapide", description=None, color_name="blue-70")
try:
    d1_fast, tel_1 = tour_rapide_tel(f"{annee}-{grand_prix}-{session_type}", tours, pilote_1)
    fig = px.line(tel_1, x='Distance', y='Speed', title=f"Tour le plus rapide – {pilote_1}", labels={'Speed': 'Vitesse (km/h)', 'Distance': 'Distance (m)'})
    if pilote_2:
        d2_fast, tel_2 = tour_rapide_tel(f"{annee}-{grand_prix}-{session_type}", tours, pilote_2)
        fig.add_scatter(x=tel_2['Distance'], y=tel_2['Speed'], mode='lines', name=pilote_2)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(f"Meilleur tour {pilote_1}", formatage_timedelta(d1_fast['LapTime']))
        lap_no_1 = _get_best_lap_no(d1_fast)
        if lap_no_1 is not None:
            st.metric("Tour du meilleur tour", f"{lap_no_1}")
    if pilote_2:
        with c2:
            st.metric(f"Meilleur tour {pilote_2}", formatage_timedelta(d2_fast['LapTime']))
            lap_no_2 = _get_best_lap_no(d2_fast)
            if lap_no_2 is not None:
                st.metric("Tour du meilleur tour", f"{lap_no_2}")

            with c3:# Calcul de la différence absolue entre les deux temps
                diff = abs(d2_fast['LapTime'] - d1_fast['LapTime'])
                difference = formatage_timedelta(diff)

                st.metric("Différence", f"{difference}")
except Exception as e:
    st.info("Télémétrie indisponible pour cette session/pilote.")
    with st.expander("Détails techniques (debug)"):
        st.write(e)


colored_header("Informations par tour un pilote", description=None, color_name="blue-70")
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