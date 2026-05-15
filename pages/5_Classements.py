import streamlit as st
from src.config import configure_page
from src.ui import selections_courantes
from src.data import (
    chargement_session,
    classement_session,
    calcul_classement_pilote,
    calcul_classement_constructeur,
)

configure_page("F1 Analytics – Classements")

t1, t2 = st.tabs(["Classement session", "Championnat"])

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

if not loaded:
    st.info("Charge d’abord une session depuis la page Home")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
tours = data["tours"]
resultats = data["resultats"]

with t1:
    st.subheader(f"Classement – {session_type}")
    cls = classement_session(tours, resultats, session_type)
    if not cls.empty:
        st.write(cls.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("Classement indisponible pour cette session.")

with t2:
    ctab1, ctab2 = st.tabs(["Pilotes", "Constructeurs"])
    with ctab1:
        st.subheader("Championnat Pilotes (cumul jusqu'à l'épreuve sélectionnée)")
        with st.spinner("Calcul des points cumulés pilotes..."):
            standings = calcul_classement_pilote(annee, grand_prix)
        if not standings.empty:
            st.write(standings.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("Classement pilotes indisponible (données incomplètes ou accès réseau).")
    with ctab2:
        st.subheader("Championnat Constructeurs (cumul jusqu'à l'épreuve sélectionnée)")
        with st.spinner("Calcul des points cumulés constructeurs..."):
            cstand = calcul_classement_constructeur(annee, grand_prix)
        if not cstand.empty:
            st.write(cstand.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("Classement constructeurs indisponible (données incomplètes ou accès réseau).")
