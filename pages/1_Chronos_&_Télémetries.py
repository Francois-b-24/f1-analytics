import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.config import configure_page
from src.ui import selecteurs_pilotes, selections_courantes
from src.data import chargement_session, tour_rapide_tel
from src.utils import formatage_timedelta
from src.analytics import delta_time_vs_distance

from streamlit_extras.colored_header import colored_header


configure_page("F1 Analytics – Tours & Chronos")

st.subheader("Tours & Chronos")
st.caption("Comparaison des performances entre 2 pilotes possible.")

# 1) Récupérer les sélections faites sur Home
annee, grand_prix, session_type, loaded = selections_courantes(required=True)
if not loaded:
    st.warning("Aucune session n'est chargée. Retournez à l'accueil.")
    st.page_link("Home.py", label="🏠 Retour à la Home")
    st.stop()

# 2) Charger les données une seule fois (cache côté src.data)
data = chargement_session(annee, grand_prix, session_type)
sess = data["session"]
tours = data["tours"]
pilotes = data["pilotes"]

# Sélecteurs pilotes dans la sidebar
with st.sidebar:
    pilote_1, pilote_2 = selecteurs_pilotes(pilotes)

subset = tours[tours['Driver'].isin([d for d in [pilote_1, pilote_2] if d])].copy()

colored_header("Évolution des temps au tour (en secondes)", description=None, color_name="blue-70")
if not subset.empty and subset['LapSeconds'].notna().any():
    fig = px.line(subset, x='LapNumber', y='LapSeconds', color='Driver', labels={'LapSeconds': 'Temps (s)'})
    fig.update_xaxes(title_text="Tours")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Données de tours insuffisantes.")


def _get_best_lap_no(d):
    """Retourne le numéro du tour du meilleur tour depuis un objet Lap."""
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
    d1_fast, tel_1 = tour_rapide_tel(sess, pilote_1)
    fig = px.line(
        tel_1, x='Distance', y='Speed',
        title=f"Tour le plus rapide – {pilote_1}",
        labels={'Speed': 'Vitesse (km/h)', 'Distance': 'Distance (m)'},
    )
    d2_fast = None
    tel_2 = None
    if pilote_2:
        d2_fast, tel_2 = tour_rapide_tel(sess, pilote_2)
        fig.add_scatter(x=tel_2['Distance'], y=tel_2['Speed'], mode='lines', name=pilote_2)
    st.plotly_chart(fig, use_container_width=True)

    # Metrics — ne génère les colonnes que pour les pilotes réellement présents
    if pilote_2:
        c1, c2, c3 = st.columns(3)
    else:
        c1, c2 = st.columns(2)
        c3 = None

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
        with c3:
            diff = abs(d2_fast['LapTime'] - d1_fast['LapTime'])
            st.metric("Différence", formatage_timedelta(diff))

    # --- F3 : Delta time overlay (si 2 pilotes sélectionnés) ---
    if pilote_2 and tel_2 is not None:
        colored_header(
            "Delta time cumulé (référence : pilote 1)",
            description="Courbe d'écart temporel aligné sur la distance parcourue. "
                        "Delta > 0 ⇒ pilote 2 en retard ; pentes = zones d'avantage.",
            color_name="blue-70",
        )
        delta_df = delta_time_vs_distance(tel_1, tel_2)
        if not delta_df.empty:
            fig_delta = go.Figure()
            fig_delta.add_trace(
                go.Scatter(
                    x=delta_df["Distance"],
                    y=delta_df["Delta"],
                    mode="lines",
                    name=f"Δ ({pilote_2} − {pilote_1})",
                    line=dict(width=2),
                )
            )
            fig_delta.add_hline(y=0, line_dash="dash", line_color="gray")
            fig_delta.update_layout(
                xaxis_title="Distance (m)",
                yaxis_title=f"Δ temps (s) — négatif = {pilote_2} devant",
                hovermode="x unified",
            )
            st.plotly_chart(fig_delta, use_container_width=True)
            final_delta = float(delta_df["Delta"].iloc[-1])
            st.caption(
                f"Écart final sur le tour : **{final_delta:+.3f} s** "
                f"({'avantage ' + pilote_1 if final_delta > 0 else 'avantage ' + pilote_2})"
            )
        else:
            st.info("Delta time indisponible (télémétries incompatibles).")
except Exception as e:
    st.warning(f"Télémétrie indisponible : **{type(e).__name__}** — {e}")
    with st.expander("Détails techniques"):
        import traceback
        st.code(traceback.format_exc())


colored_header("Informations par tour un pilote", description=None, color_name="blue-70")
colonnes = ['Driver', 'LapNumber', 'LapTime', 'LapSeconds', 'Compound', 'Stint', 'IsPersonalBest', 'PitOutTime', 'PitInTime']
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
