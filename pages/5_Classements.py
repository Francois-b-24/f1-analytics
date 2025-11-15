import streamlit as st
from scr.config import configure_page
from scr.ui import selections_courantes, render_team_logo, render_driver_img
from scr.data import chargement_session, classement_session, calcul_classement_pilote, calcul_classement_constructeur

configure_page("F1 Analytics – Classements")

with open("f1_theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

t1, t2 = st.tabs(["Classement session", "Championnat"])

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = chargement_session(annee, grand_prix, session_type)
tours = data["tours"]
pilotes = data["pilotes"]

if not loaded:
    st.info("Charge d’abord une session depuis la page Home")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
tours = data['tours']
resultats = data['resultats']

with t1:
    st.subheader(f"Classement – {session_type}")
    cls = classement_session(tours, resultats, session_type)
    if not cls.empty:
        # Ajout logos : TeamName + Driver
        df = cls.copy()
        if "TeamName" in df:
            df["TeamName"] = df["TeamName"].apply(lambda team: render_team_logo(team, 22))
        if "BroadcastName" in df and "DriverNumber" in df:
            # On pourrait matcher code pilote ici, mais absence parfois donc passons juste le nom
            df["BroadcastName"] = df["BroadcastName"].apply(lambda name: name)
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("Classement indisponible pour cette session.")

with t2:
    ctab1, ctab2 = st.tabs(["Pilotes", "Constructeurs"])
    with ctab1:
        st.subheader("Championnat Pilotes (cumul jusqu'à l'épreuve sélectionnée)")
        with st.spinner("Calcul des points cumulés pilotes..."):
            standings = calcul_classement_pilote(annee, grand_prix)
        if not standings.empty:
            df = standings.copy()
            if "TeamName" in df:
                df["TeamName"] = df["TeamName"].apply(lambda team: render_team_logo(team, 22))
            if "BroadcastName" in df:
                # Pilote : pas systématique d'avoir code rapide, on garde juste nom ou on peut mettre photo si mapping dispo
                df["BroadcastName"] = df["BroadcastName"].apply(lambda name: name)
            st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("Classement pilotes indisponible (données incomplètes ou accès réseau).")
    with ctab2:
        st.subheader("Championnat Constructeurs (cumul jusqu'à l'épreuve sélectionnée)")
        with st.spinner("Calcul des points cumulés constructeurs..."):
            cstand = calcul_classement_constructeur(annee, grand_prix)
        if not cstand.empty:
            df = cstand.copy()
            if "TeamName" in df:
                df["TeamName"] = df["TeamName"].apply(lambda team: render_team_logo(team, 26))
            st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("Classement constructeurs indisponible (données incomplètes ou accès réseau).")