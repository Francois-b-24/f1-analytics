import streamlit as st
from src.session import charger_session_ou_stopper
from src.data import figure_positions_par_tour
from src.ui import selections_courantes, afficher_figure, entete_page

entete_page("positions")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

# Les positions par tour n'existent que pour les courses. L'avertissement était
# auparavant affiché en toutes circonstances, y compris en course où il est faux.
if session_type != "R":
    st.info(
        "Les positions par tour ne sont publiées que pour les **courses**. "
        "Choisissez une session de type « Course » dans la barre latérale."
    )
    st.stop()

data = charger_session_ou_stopper(annee, grand_prix, session_type)
tours = data["tours"]

pilotes = sorted(tours["Driver"].dropna().unique()) if "Driver" in tours else []
selection = st.multiselect(
    "Mettre en évidence (vide = tous les pilotes)",
    pilotes,
    default=[],
    help="Isoler quelques pilotes rend les croisements de lignes plus lisibles.",
)

afficher_figure(figure_positions_par_tour(tours, pilotes=selection or None))