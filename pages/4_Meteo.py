import streamlit as st
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from scr.config import configure_page
from scr.ui import selections_courantes
from scr.data import chargement_session

configure_page("F1 Analytics – Météo")

st.subheader("Données météo de la session")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = chargement_session(annee, grand_prix, session_type)
tours = data["tours"]
pilotes = data["pilotes"]

if not loaded:
    st.info("Charge d’abord une session depuis la page Home")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
meteo = data['meteo']

if not meteo.empty:
    st.dataframe(meteo, use_container_width=True)
    xcol = 'SessionTimeSec' if 'SessionTimeSec' in meteo else 'Time'
    # --- KPI : Écart moyen entre la température piste et air ---
    if 'AirTemp' in meteo and 'TrackTemp' in meteo:
        try:
            diff = meteo['TrackTemp'] - meteo['AirTemp']
            mean_diff = float(diff.mean(skipna=True))
            st.metric("Écart moyen piste - air", f"{mean_diff:.1f} °C")
        except Exception:
            pass

    temp = ('AirTemp' in meteo) or ('TrackTemp' in meteo)

    if temp:
        fig_all = make_subplots(specs=[[{"secondary_y": True}]])
        if 'AirTemp' in meteo:
            fig_all.add_trace(
                go.Scatter(x=meteo[xcol], y=meteo['AirTemp'], mode='lines', name='Température air (°C)'),
                secondary_y=False,
            )
        if 'TrackTemp' in meteo:
            fig_all.add_trace(
                go.Scatter(x=meteo[xcol], y=meteo['TrackTemp'], mode='lines', name='Température piste (°C)'),
                secondary_y=False,
            )
        fig_all.update_layout(
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
            margin=dict(l=40, r=20, t=60, b=40),
        )
        fig_all.update_xaxes(title_text='Temps de session')
        fig_all.update_yaxes(title_text='Température (°C)', secondary_y=False)

        st.plotly_chart(fig_all, use_container_width=True)

    if 'AirTemp' in meteo:
        fig_t = px.line(meteo, x=xcol, y='AirTemp', labels={'AirTemp':'Température air (°C)'}, title="Température de l'air")
        fig_t.update_xaxes(title_text="Temps de session")
        st.plotly_chart(fig_t, use_container_width=True)
    if 'TrackTemp' in meteo:
        fig_tt = px.line(meteo, x=xcol, y='TrackTemp', labels={'TrackTemp':'Température piste (°C)'}, title="Température de la piste")
        fig_tt.update_xaxes(title_text="Temps de session")
        st.plotly_chart(fig_tt, use_container_width=True)
    if 'WindSpeed' in meteo:
        fig_w = px.line(meteo, x=xcol, y='WindSpeed', labels={'WindSpeed':'Vent (m/s)'}, title="Vitesse du vent")
        fig_w.update_xaxes(title_text="Temps de session")
        st.plotly_chart(fig_w, use_container_width=True)


else:
    st.info("Météo indisponible pour cette session.")