from asyncio import set_event_loop

import streamlit as st
from scr.config import configure_page
from scr.ui import selections_courantes
from scr.data import chargement_session

configure_page("F1 Analytics – Export & Données")

st.subheader("Exports rapides")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = chargement_session(annee, grand_prix, session_type)
tours = data["tours"]
pilotes = data["pilotes"]

if not loaded:
    st.info("Charge d’abord une session depuis la Home.")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
tours = data['tours']
meteo = data['meteo']
resultats = data['resultats']

if not tours.empty:
    csv = tours.to_csv(index=False).encode('utf-8')
    st.download_button("Télécharger tous les tours (CSV)", data=csv,
                       file_name=f"laps_full_{annee}_{grand_prix}_{session_type}.csv", mime="text/csv")
if not meteo.empty:
    csvw = meteo.to_csv(index=False).encode('utf-8')
    st.download_button("Télécharger météo (CSV)", data=csvw,
                       file_name=f"weather_{annee}_{grand_prix}_{session_type}.csv", mime="text/csv")
if not resultats.empty:
    csvr = resultats.to_csv(index=False).encode('utf-8')
    st.download_button("Télécharger résultats (CSV)", data=csvr,
                       file_name=f"results_{annee}_{grand_prix}_{session_type}.csv", mime="text/csv")