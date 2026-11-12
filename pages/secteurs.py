import streamlit as st
import plotly.express as px

from src.ui import selections_courantes, entete_page
from src.session import charger_session_ou_stopper
from src.analytics import sector_times_long, sector_best_per_driver
from streamlit_extras.colored_header import colored_header


entete_page("secteurs")
st.caption(
    "Décomposition des temps au tour en 3 secteurs. Permet d'identifier "
    "dans quelle portion du circuit un pilote gagne ou perd du temps."
)

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = charger_session_ou_stopper(annee, grand_prix, session_type)
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
colored_header("Meilleurs temps par secteur", description="Delta vs meilleur pilote du secteur", color_name="blue-70")
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
colored_header("Distribution des temps par secteur", description=None, color_name="blue-70")
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
    st.plotly_chart(fig_box, width="stretch")

    # Évolution des temps de secteur par numéro de tour
    colored_header("Évolution des temps par secteur", description=None, color_name="blue-70")
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
    st.plotly_chart(fig_evo, width="stretch")
