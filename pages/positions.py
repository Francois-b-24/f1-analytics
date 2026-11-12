import streamlit as st

from src.analytics import bilan_positions, changements_de_position
from src.data import figure_positions_par_tour
from src.session import charger_session_ou_stopper
from src.ui import afficher_figure, entete_page, selections_courantes

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

# Dérivé des tours déjà chargés : aucune requête réseau supplémentaire.
bilan = bilan_positions(tours)

if bilan.empty:
    st.info(
        "Les positions ne sont pas encore publiées pour cette course. "
        "Elles apparaissent généralement quelques heures après l'arrivée."
    )
    st.stop()

meilleure = bilan.iloc[0]
pire = bilan.iloc[-1]

c1, c2, c3 = st.columns(3)
c1.metric(
    "Plus belle remontée",
    meilleure["Pilote"],
    delta=f"{int(meilleure['Solde']):+d} places",
    help="Écart entre la position au premier tour et celle au dernier tour.",
    border=True,
)
c2.metric(
    "Plus forte chute",
    pire["Pilote"],
    delta=f"{int(pire['Solde']):+d} places",
    help="Un abandon ou un problème technique se traduit ici par une chute.",
    border=True,
)
c3.metric(
    "Changements de position",
    changements_de_position(tours),
    help=("Mesure l'agitation de la course. Ce n'est pas un décompte de "
          "dépassements : un arrêt aux stands en produit aussi, et les "
          "données ne permettent pas de les distinguer."),
    border=True,
)

st.subheader("Évolution au fil des tours")

pilotes = sorted(tours["Driver"].dropna().unique()) if "Driver" in tours else []
selection = st.multiselect(
    "Mettre en évidence (vide = tous les pilotes)",
    pilotes,
    default=[],
    help="Isoler quelques pilotes rend les croisements de lignes plus lisibles.",
)

afficher_figure(figure_positions_par_tour(tours, pilotes=selection or None))

st.subheader("Bilan par pilote")
st.caption(
    "Un solde positif signifie que le pilote a gagné des places entre le "
    "premier et le dernier tour. « Meilleure position » est la plus haute "
    "atteinte en course, même brièvement."
)
st.dataframe(
    bilan,
    hide_index=True,
    width="stretch",
    column_config={
        "Solde": st.column_config.NumberColumn("Solde", format="%+d"),
        "MeilleurePosition": st.column_config.NumberColumn("Meilleure position"),
    },
)
