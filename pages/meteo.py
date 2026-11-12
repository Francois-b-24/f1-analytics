import pandas as pd
import streamlit as st
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from src.ui import selections_courantes, entete_page
from src.session import charger_session_ou_stopper

entete_page("meteo")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)


data = charger_session_ou_stopper(annee, grand_prix, session_type)
meteo = data["meteo"]

if not meteo.empty:
    xcol = 'SessionTimeSec' if 'SessionTimeSec' in meteo else 'Time'
    # --- KPI : Écart moyen entre la température piste et air ---
    if 'AirTemp' in meteo and 'TrackTemp' in meteo:
        diff = meteo['TrackTemp'] - meteo['AirTemp']
        mean_diff = float(diff.mean(skipna=True))
        if pd.notna(mean_diff):
            st.metric(
                "Écart moyen piste − air",
                f"{mean_diff:.1f} °C",
                help=("Une piste nettement plus chaude que l'air accélère la "
                      "dégradation des pneus et pousse à s'arrêter plus tôt."),
                border=True,
            )

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

        st.plotly_chart(fig_all, width="stretch")

    # Air et piste sont déjà tracées ensemble au-dessus : les reprendre
    # séparément n'ajoutait rien. Le vent, lui, est une donnée distincte.
    if 'WindSpeed' in meteo:
        fig_w = px.line(
            meteo, x=xcol, y='WindSpeed',
            labels={'WindSpeed': 'Vent (m/s)'}, title="Vitesse du vent",
        )
        fig_w.update_xaxes(title_text="Temps de session")
        st.plotly_chart(fig_w, width="stretch")

    with st.expander("Données brutes"):
        st.dataframe(meteo, hide_index=True, width="stretch")

else:
    st.info("Météo indisponible pour cette session.")