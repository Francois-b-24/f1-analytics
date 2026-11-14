import streamlit as st
import plotly.express as px

from src.config import configure_page
from src.ui import page_session
from src.analytics import sector_times_long, sector_best_per_driver


configure_page("F1 Analytics – Analyse par secteur")


data, annee, grand_prix, session_type = page_session(
    "Secteurs", "📐",
    "Décomposition des temps au tour en 3 secteurs : où un pilote gagne ou perd du temps.",
)
tours = data["tours"]
pilotes = data["pilotes"]

if not {"Sector1TimeSec", "Sector2TimeSec", "Sector3TimeSec"}.issubset(tours.columns):
    st.info("Les temps par secteur ne sont pas disponibles pour cette session.")
    st.stop()

# Sélection de pilotes
default_drivers = pilotes[: min(6, len(pilotes))]
selected = st.multiselect(
    "Pilotes à afficher",
    options=pilotes,
    default=default_drivers,
    key="sector_drivers",
)
if not selected:
    st.info("Sélectionne au moins un pilote.")
    st.stop()

# ---------------------------------------------------------------------------
# Tableau des meilleurs temps par secteur
# ---------------------------------------------------------------------------
st.markdown("### " + "Meilleurs temps par secteur")
st.caption("Delta vs meilleur pilote du secteur")
best = sector_best_per_driver(tours[tours["Driver"].isin(selected)])
if best.empty:
    st.info("Données insuffisantes.")
else:
    display = best.copy()
    for c in ("S1", "S2", "S3", "Total"):
        if c in display.columns:
            display[c] = display[c].round(3)
    for c in ("DeltaS1", "DeltaS2", "DeltaS3", "DeltaTotal"):
        if c in display.columns:
            display[c] = display[c].round(3)
    st.dataframe(display, width="stretch")

# ---------------------------------------------------------------------------
# Distribution des temps par secteur (box-plot)
# ---------------------------------------------------------------------------
st.markdown("### " + "Distribution des temps par secteur")
long = sector_times_long(tours, drivers=selected)
if long.empty:
    st.info("Données insuffisantes pour la distribution.")
else:
    fig_box = px.box(
        long,
        x="Driver",
        y="Seconds",
        color="Driver",
        facet_col="Sector",
        points="outliers",
        labels={"Seconds": "Temps (s)", "Driver": "Pilote"},
    )
    fig_box.update_yaxes(matches=None, showticklabels=True)
    fig_box.update_layout(showlegend=False, height=450)
    st.plotly_chart(fig_box, use_container_width=True)

    # Évolution des temps de secteur par numéro de tour
    st.markdown("### " + "Évolution des temps par secteur")
    fig_evo = px.line(
        long.sort_values("LapNumber"),
        x="LapNumber",
        y="Seconds",
        color="Driver",
        facet_row="Sector",
        labels={"LapNumber": "Tour", "Seconds": "Temps (s)"},
        height=700,
    )
    fig_evo.update_yaxes(matches=None)
    st.plotly_chart(fig_evo, use_container_width=True)
