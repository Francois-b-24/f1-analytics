import streamlit as st
from src.config import configure_page
from src.data import (
    calcul_classement_constructeur,
    calcul_classement_pilote,
    classement_session,
)
from src.ui import page_session

configure_page("F1 Analytics – Classements")

data, annee, grand_prix, session_type = page_session(
    "Classements", "🏆",
    "Classement de la session et championnats pilotes et constructeurs.",
)

# Les onglets sont créés après le préambule : construits avant, ils
# s'affichaient vides quand aucune session n'était chargée.
t1, t2 = st.tabs(["Classement session", "Championnat"])

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
