import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import configure_page
from src.ui import selections_courantes
from src.data import chargement_session
from src.analytics import (
    stint_degradation,
    stint_degradation_fits,
    tyre_degradation_matrix,
)

configure_page("F1 Analytics – Pneus & Stratégie")

st.subheader("Pneus & Stratégie")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

if not loaded:
    st.info("Charge d’abord une session depuis la page Home.")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
tours = data["tours"]
pilotes = data["pilotes"]

# ---------------------------------------------------------------------------
# Stints par pilote
# ---------------------------------------------------------------------------
st.subheader("Stints par pilote")
if {'Stint', 'Compound', 'LapNumber'}.issubset(tours.columns):
    stint_ranges = (
        tours.dropna(subset=['Stint'])
        .groupby(['Driver', 'Stint'])
        .agg(StartLap=('LapNumber', 'min'), EndLap=('LapNumber', 'max'),
             Compound=('Compound', 'last'))
        .reset_index()
    )
    st.dataframe(stint_ranges, use_container_width=True)

    st.subheader("Performance moyenne par stint (temps moyen)")
    perf = (
        tours.dropna(subset=['LapSeconds', 'Stint'])
        .groupby(['Driver', 'Stint', 'Compound'])['LapSeconds']
        .mean()
        .reset_index(name='AvgLapSec')
    )
    fig = px.bar(
        perf, x='Driver', y='AvgLapSec', color='Compound',
        barmode='group', facet_row='Stint',
        labels={'AvgLapSec': 'Temps moyen (s)'},
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Les informations de stints/pneus ne sont pas disponibles pour cette session.")
    st.stop()

# ---------------------------------------------------------------------------
# F2 — Modèle de dégradation de stint
# ---------------------------------------------------------------------------
st.subheader("Dégradation des pneus par stint")
st.caption(
    "Régression linéaire LapTime ~ TyreLife par stint. "
    "Les in/out laps et les outliers (IQR×1.5) sont exclus. "
    "La **pente** représente la dégradation en secondes/tour."
)

driver_options = sorted(tours["Driver"].dropna().unique().tolist())
default_drivers = driver_options[: min(4, len(driver_options))]
selected_drivers = st.multiselect(
    "Pilotes à inclure",
    options=driver_options,
    default=default_drivers,
    key="deg_drivers",
)

if selected_drivers:
    deg_df = stint_degradation(tours, drivers=selected_drivers)
    if deg_df.empty:
        st.info("Données insuffisantes pour estimer la dégradation (stints trop courts ou données manquantes).")
    else:
        fits = stint_degradation_fits(deg_df)

        # Scatter + droite de régression par (Driver, Stint)
        fig_deg = px.scatter(
            deg_df,
            x="TyreLife",
            y="LapSeconds",
            color="Driver",
            symbol="Compound",
            facet_col="Driver",
            facet_col_wrap=min(3, len(selected_drivers)),
            labels={"TyreLife": "Âge pneu (tours)", "LapSeconds": "Temps au tour (s)"},
            height=max(350, 300 * ((len(selected_drivers) + 2) // 3)),
        )

        # Overlay des droites de régression
        for _, row in fits.iterrows():
            drv_df = deg_df[(deg_df["Driver"] == row["Driver"]) & (deg_df["Stint"] == row["Stint"])]
            if drv_df.empty:
                continue
            xs = np.array([drv_df["TyreLife"].min(), drv_df["TyreLife"].max()])
            ys = row["Slope"] * xs + row["Intercept"]
            fig_deg.add_trace(
                go.Scatter(
                    x=xs, y=ys, mode="lines",
                    line=dict(dash="dot", width=1.5),
                    name=f"{row['Driver']} S{row['Stint']}",
                    showlegend=False,
                ),
                row="all", col="all",
            )
        fig_deg.update_yaxes(matches=None)
        st.plotly_chart(fig_deg, use_container_width=True)

        if not fits.empty:
            st.markdown("**Estimations par stint**")
            display = fits.copy()
            display["Slope"] = display["Slope"].round(3)
            display["Intercept"] = display["Intercept"].round(3)
            display["R2"] = display["R2"].round(3)
            display = display.rename(columns={"Slope": "Slope (s/tour)", "Intercept": "Base (s)"})
            st.dataframe(display, use_container_width=True)

# ---------------------------------------------------------------------------
# F4 — Heatmap de dégradation (Driver × LapNumber → Δ au PB personnel)
# ---------------------------------------------------------------------------
st.subheader("Heatmap LapTime (Δ vs meilleur tour personnel)")
st.caption(
    "Chaque cellule = écart du tour vs le meilleur tour personnel du pilote. "
    "Identifie visuellement les relais dégradés, les undercuts et les tours perturbés."
)
mat = tyre_degradation_matrix(tours)
if mat.empty:
    st.info("Pas de données suffisantes pour la heatmap.")
else:
    # Cap l'échelle pour éviter qu'un outlier n'écrase la lecture
    vmax = float(np.nanpercentile(mat.values, 95))
    fig_hm = px.imshow(
        mat,
        aspect="auto",
        color_continuous_scale="RdYlGn_r",
        zmin=0,
        zmax=max(vmax, 1.0),
        labels=dict(x="Numéro de tour", y="Pilote", color="Δ vs PB (s)"),
    )
    fig_hm.update_layout(height=max(380, 22 * len(mat.index) + 120))
    st.plotly_chart(fig_hm, use_container_width=True)
