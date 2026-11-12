import pandas as pd
import streamlit as st

from src.session import charger_session_ou_stopper
from src.ui import entete_page, selections_courantes

entete_page("exports")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = charger_session_ou_stopper(annee, grand_prix, session_type)


def _best_laps_en_table(best_laps) -> pd.DataFrame:
    """`best_laps` est un dict {code pilote: infos} — le remettre à plat.

    Ce jeu de données faisait partie du contrat de `chargement_session` mais
    n'avait jamais été exporté.
    """
    if not best_laps:
        return pd.DataFrame()
    lignes = [{"Driver": code, **infos} for code, infos in best_laps.items()]
    return pd.DataFrame(lignes)


# Libellé affiché -> (DataFrame, préfixe du nom de fichier)
JEUX: dict[str, tuple[pd.DataFrame, str]] = {
    "Tours": (data["tours"], "tours"),
    "Météo": (data["meteo"], "meteo"),
    "Résultats": (data["resultats"], "resultats"),
    "Meilleurs tours": (_best_laps_en_table(data.get("best_laps")), "meilleurs_tours"),
}

disponibles = [nom for nom, (df, _) in JEUX.items() if df is not None and not df.empty]

if not disponibles:
    st.info("Aucune donnée exportable pour cette session.")
    st.stop()

choix = st.segmented_control(
    "Jeu de données",
    disponibles,
    default=disponibles[0],
    help="Les fichiers reprennent les données telles qu'affichées dans l'application.",
)
# `segmented_control` renvoie None si l'utilisateur déselectionne l'option active.
choix = choix or disponibles[0]

df, prefixe = JEUX[choix]

c1, c2 = st.columns(2)
c1.metric("Lignes", f"{len(df):,}".replace(",", " "), border=True)
c2.metric("Colonnes", df.shape[1], border=True)

st.subheader("Aperçu")
st.caption(
    f"Les {min(50, len(df))} premières lignes sur {len(df)}. "
    "Le téléchargement contient l'intégralité du jeu de données."
)
st.dataframe(df.head(50), hide_index=True, width="stretch")

nom_gp = str(grand_prix).replace(" ", "_").replace("(", "").replace(")", "")
st.download_button(
    f"Télécharger « {choix} » (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"{prefixe}_{annee}_{nom_gp}_{session_type}.csv",
    mime="text/csv",
    type="primary",
    icon=":material/download:",
)
