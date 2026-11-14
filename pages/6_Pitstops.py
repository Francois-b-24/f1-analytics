import streamlit as st
from src.config import configure_page
from src.ui import page_session
from src.utils import formatage_timedelta

configure_page("F1 Analytics – Arrêts aux stands")


data, annee, grand_prix, session_type = page_session(
    "Arrêts aux stands", "🔧",
    "Arrêts détectés à partir des tours d'entrée et de sortie des stands.",
)
tours = data["tours"]

st.subheader("Arrêts détectés")
if 'PitInTime' in tours or 'PitOutTime' in tours or 'PitStop' in tours:
    pits = tours.copy()
    cols = [c for c in ['Driver', 'LapNumber', 'PitInTime', 'PitOutTime', 'PitStop', 'Compound'] if c in pits.columns]
    pits = pits[cols]
    mask = False
    if 'PitInTime' in pits:
        mask = mask | pits['PitInTime'].notna()
    if 'PitOutTime' in pits:
        mask = mask | pits['PitOutTime'].notna()
    if 'PitStop' in pits:
        mask = mask | (pits['PitStop'].fillna(0).astype(int) > 0)
    pits = pits[mask]
    for c in ['PitInTime', 'PitOutTime']:
        if c in pits:
            pits[c] = pits[c].apply(formatage_timedelta)
    st.dataframe(pits, width="stretch")
else:
    st.info("Aucune donnée d'arrêt aux stands disponible.")
