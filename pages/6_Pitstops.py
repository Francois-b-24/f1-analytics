import streamlit as st
from scr.config import configure_page
from scr.ui import selections_courantes
from scr.data import chargement_session
from scr.utils import formatage_timedelta

with open("f1_theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

configure_page("F1 Analytics – Arrêts aux stands")

st.subheader("Arrêts aux stands")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = chargement_session(annee, grand_prix, session_type)
tours = data["tours"]
pilotes = data["pilotes"]

if not loaded:
    st.info("Charge d’abord une session depuis la Home.")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
tours = data['tours']

st.subheader("Arrêts détectés")
if 'PitInTime' in tours or 'PitOutTime' in tours or 'PitStop' in tours:
    pits = tours.copy()
    cols = [c for c in ['Driver','LapNumber','PitInTime','PitOutTime','PitStop','Compound'] if c in pits.columns]
    pits = pits[cols]
    mask = False
    if 'PitInTime' in pits:  mask = mask | pits['PitInTime'].notna()
    if 'PitOutTime' in pits: mask = mask | pits['PitOutTime'].notna()
    if 'PitStop' in pits:    mask = mask | pits['PitStop'].fillna(0).astype(int) > 0
    pits = pits[mask]
    for c in ['PitInTime','PitOutTime']:
        if c in pits:
            pits[c] = pits[c].apply(formatage_timedelta)
    st.dataframe(pits, use_container_width=True)
else:
    st.info("Aucune donnée d'arrêt aux stands disponible.")