import streamlit as st
from src.ui import entete_page, selections_courantes
from src.session import charger_session_ou_stopper
from src.data import (
    classement_session,
    calcul_classement_pilote,
    calcul_classement_constructeur,
)

entete_page("classements")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = charger_session_ou_stopper(annee, grand_prix, session_type)
tours = data["tours"]
resultats = data["resultats"]

# Onglets créés après la garde : sinon ils s'affichent, vides, au-dessus du
# message expliquant qu'aucune session n'est chargée.
t1, t2 = st.tabs(["Classement session", "Championnat"])

with t1:
    st.subheader(f"Classement – {session_type}")
    cls = classement_session(tours, resultats, session_type)
    if not cls.empty:
        st.dataframe(cls, hide_index=True, width="stretch")
    else:
        st.info("Classement indisponible pour cette session.")

with t2:
    ctab1, ctab2 = st.tabs(["Pilotes", "Constructeurs"])
    with ctab1:
        st.subheader("Championnat Pilotes (cumul jusqu'à l'épreuve sélectionnée)")
        with st.spinner("Calcul des points cumulés pilotes..."):
            standings = calcul_classement_pilote(annee, grand_prix)
        if not standings.empty:
            st.dataframe(standings, hide_index=True, width="stretch")
        else:
            st.info("Classement pilotes indisponible (données incomplètes ou accès réseau).")
    with ctab2:
        st.subheader("Championnat Constructeurs (cumul jusqu'à l'épreuve sélectionnée)")
        with st.spinner("Calcul des points cumulés constructeurs..."):
            cstand = calcul_classement_constructeur(annee, grand_prix)
        if not cstand.empty:
            st.dataframe(cstand, hide_index=True, width="stretch")
        else:
            st.info("Classement constructeurs indisponible (données incomplètes ou accès réseau).")
