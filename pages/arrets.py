import plotly.express as px
import streamlit as st

from src.analytics import arrets_par_equipe, arrets_par_pilote, resume_arrets
from src.pedagogie import aide
from src.session import charger_session_ou_stopper
from src.theme import COMPOSES, ORDRE_COMPOSES
from src.ui import entete_page, selections_courantes

entete_page("arrets")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = charger_session_ou_stopper(annee, grand_prix, session_type)
tours = data["tours"]

# Tout est dérivé des tours déjà chargés : aucune requête réseau de plus.
arrets = arrets_par_pilote(tours)

if arrets.empty:
    st.info(
        "Aucun arrêt aux stands n'est renseigné pour cette session. "
        "C'est normal en essais libres, et les données de course peuvent "
        "mettre quelques heures à être publiées."
    )
    st.stop()

resume = resume_arrets(arrets)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Arrêts", resume["nombre"], border=True)
c2.metric(
    "Durée médiane",
    f"{resume['mediane']:.2f} s",
    help=("La médiane plutôt que la moyenne : un seul arrêt problématique "
          "suffirait à déformer la moyenne."),
    border=True,
)
c3.metric(
    "Arrêt le plus rapide",
    f"{resume['plus_rapide']:.2f} s",
    delta=resume["pilote_plus_rapide"],
    delta_color="off",
    border=True,
)
c4.metric(
    "Pilotes concernés",
    resume["pilotes"],
    help="Un pilote absent n'a pas effectué d'arrêt, ou a abandonné avant.",
    border=True,
)

st.caption(
    "La durée affichée est l'immobilisation dans le stand. Elle n'inclut pas "
    "le ralentissement dans la voie des stands, qui alourdit encore la perte "
    "réelle de quelques secondes."
)

st.subheader("Durée de chaque arrêt")

# Coloration par composé chaussé à la sortie : les teintes viennent du thème,
# jamais recodées ici (un composé garde la même couleur dans toute l'app).
couleur = {}
if "Composé" in arrets.columns:
    couleur = {
        "color": "Composé",
        "color_discrete_map": COMPOSES,
        "category_orders": {"Composé": list(ORDRE_COMPOSES)},
    }

fig = px.bar(
    arrets,
    x="Pilote",
    y="Duree",
    labels={"Duree": "Durée (s)", "Pilote": ""},
    hover_data=[c for c in ("Tour", "Equipe") if c in arrets.columns],
    **couleur,
)
fig.update_layout(barmode="group", legend_title_text="Pneu chaussé")
st.plotly_chart(fig, width="stretch")

st.subheader("Quand les arrêts ont eu lieu")
st.caption(
    "Deux pilotes d'une même écurie qui s'arrêtent à des tours différents "
    "appliquent souvent des stratégies opposées — voir « undercut » dans le "
    "glossaire."
)

fig_tours = px.scatter(
    arrets,
    x="Tour",
    y="Pilote",
    size="Duree",
    labels={"Tour": "Tour de l'arrêt", "Pilote": ""},
    hover_data=["Duree"],
    **couleur,
)
st.plotly_chart(fig_tours, width="stretch")

par_equipe = arrets_par_equipe(arrets)
if not par_equipe.empty:
    st.subheader("Rythme par écurie")
    st.caption(
        "Classé par durée médiane. Le nombre d'arrêts varie selon la stratégie "
        "et les abandons : une écurie avec un seul arrêt n'est pas comparable "
        "à une autre qui en a réalisé quatre."
    )
    st.dataframe(
        par_equipe,
        hide_index=True,
        width="stretch",
        column_config={
            "Médiane": st.column_config.NumberColumn("Médiane (s)", format="%.2f"),
            "Meilleur": st.column_config.NumberColumn("Meilleur (s)", format="%.2f"),
        },
    )

with st.expander("Détail des arrêts"):
    st.dataframe(
        arrets,
        hide_index=True,
        width="stretch",
        column_config={
            "Duree": st.column_config.NumberColumn("Durée (s)", format="%.2f"),
        },
    )
    st.caption(aide("Relais (stint)"))
