import pandas as pd
import streamlit as st

from src.pedagogie import GLOSSAIRE
from src.ui import entete_page

entete_page("glossaire")

st.subheader("Vocabulaire")

filtre = st.text_input(
    "Rechercher un terme",
    placeholder="undercut, dégradation, secteur…",
    label_visibility="collapsed",
)

termes = pd.DataFrame(
    [{"Terme": t, "Définition": d} for t, d in sorted(GLOSSAIRE.items())]
)
if filtre:
    masque = (
        termes["Terme"].str.contains(filtre, case=False, na=False)
        | termes["Définition"].str.contains(filtre, case=False, na=False)
    )
    termes = termes[masque]

if termes.empty:
    st.info(f"Aucun terme ne correspond à « {filtre} ».")
else:
    st.dataframe(
        termes,
        hide_index=True,
        width="stretch",
        column_config={
            "Terme": st.column_config.TextColumn(width="small"),
            "Définition": st.column_config.TextColumn(width="large"),
        },
    )

st.divider()

st.subheader("D'où viennent les données")
st.markdown(
    """
L'application s'appuie sur [OpenF1](https://openf1.org), qui republie les
données de chronométrage officielles de la Formule 1.

- **Couverture** : saison 2023 et suivantes. OpenF1 ne publie rien avant.
- **Délai** : les données d'une session apparaissent quelques heures après
  celle-ci. La télémétrie détaillée peut demander 24 à 48 h.
- **Classements du championnat** : calculés depuis Ergast, avec un repli sur
  un cumul des points course par course si cette source est indisponible.
"""
)

st.subheader("Ce que l'application n'a pas")
st.markdown(
    """
La Formule 1 **ne publie aucune donnée d'énergie** : ni état de charge de la
batterie, ni déploiement du MGU-K, ni aérodynamique active.

La page *Énergie & 2026* ne mesure donc rien. Elle **dérive** des indicateurs
à partir des seuls canaux publiés — le freinage comme approximation de la
récupération, la pleine charge comme approximation du déploiement. Ces valeurs
permettent de comparer des pilotes entre eux sur une même session ; elles ne
quantifient pas une énergie.

Le canal `DRS` est écarté de ces indicateurs : vérifié sur données réelles, il
ne contient que des zéros.
"""
)
