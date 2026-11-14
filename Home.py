"""Accueil de l'application — et point d'entrée historique.

Ce fichier a deux rôles, distingués par ``__name__`` :

* lancé directement (``streamlit run Home.py``), il délègue au routeur
  ``streamlit_app.py``, qui déclare explicitement les dix pages. Sans cela la
  navigation dépendrait de la découverte implicite du dossier ``pages/``, qui
  n'est active que si ce dossier est adjacent au fichier d'entrée — condition
  fausse en production, où l'app ne servait plus que l'accueil ;
* exécuté par ce routeur (``run_name="__page__"``), il rend simplement
  l'accueil, la configuration de page ayant déjà été faite en amont.
"""
import streamlit as st

if __name__ == "__main__":
    # Lancement direct : on délègue au routeur plutôt que de rendre l'accueil
    # seul. `st.navigation` y déclare les pages, donc la barre latérale existe
    # quel que soit le fichier d'entrée configuré côté hébergeur.
    import runpy
    from pathlib import Path as _Path

    runpy.run_path(
        str(_Path(__file__).resolve().parent / "streamlit_app.py"),
        run_name="__router__",
    )
    st.stop()

from src.config import configure_page_home
from src.ui import selections_courantes, sidebar_hint_once
from src.data import chargement_session
from src.utils import formatage_timedelta
from src.theme import COMPOSES, ORDRE_COMPOSES
import plotly.express as px
import pandas as pd
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space


configure_page_home("F1 Analytics – Home")

st.markdown(
    """
    <div style="text-align:center; font-size: 1.5em; font-weight: 500;">
        <span class="f1-glow"><span class="f1-car-emoji">🏎️</span> F1 Analytics</span>
    </div>
    """,
    unsafe_allow_html=True
)

# Citation Lewis Hamilton
st.markdown(
    '<div class="citation" style="text-align:center;font-size:1.1em;padding-top:0.7em;padding-bottom:0.5em;">'
    '« STILL I RISE » <span style="font-size:0.85em;">– Lewis Hamilton</span>'
    '</div>',
    unsafe_allow_html=True
)


sidebar_hint_once()

# Le sélecteur de session vit dans le routeur (`streamlit_app.py`), donc dans
# la barre latérale de toutes les pages. Le rendre aussi ici dupliquerait ses
# clés dans le même run et lèverait `StreamlitDuplicateElementKey` : l'accueil
# partirait en erreur.
annee, grand_prix, session_type, loaded = selections_courantes(required=False)

if not loaded:
    st.info(
        "Choisissez une saison, un Grand Prix et un type de session dans la "
        "barre latérale, puis **Charger**."
    )
    st.stop()

# Chargement du WEEK-END de Grand prix
import logging
_logger = logging.getLogger("f1_analytics.home")

try:
    _data = chargement_session(annee, grand_prix, session_type)
    session = session_type
    nom_gp = grand_prix
    tours = _data['tours']
    pilotes = _data['pilotes']
    meteo = _data['meteo']
    resultats = _data['resultats']
except Exception as e:
    _logger.exception("Échec chargement session %s / %s / %s", annee, grand_prix, session_type)
    err_type = type(e).__name__
    msg = str(e) or "(pas de message)"

    if "404" in msg or "not found" in msg.lower() or "no data" in msg.lower():
        st.error(f"❌ Session indisponible : {annee} – {grand_prix} ({session_type}). Cette session n'a pas encore eu lieu ou n'est pas publiée.")
    elif "connection" in msg.lower() or "timeout" in msg.lower() or err_type in ("ConnectionError", "Timeout"):
        st.error("🔌 Problème de connexion à l'API F1. Réessaie dans quelques instants.")
    else:
        st.error(f"⚠️ Impossible de charger cette session : **{err_type}** — {msg}")

    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔄 Réessayer", key="retry_load"):
            chargement_session.clear()
            st.rerun()
    with st.expander("Détails techniques"):
        import traceback
        st.code(f"{err_type}: {msg}\n\n{traceback.format_exc()}")
    st.stop()


# Les métriques utilisent maintenant le thème CSS adaptatif

colored_header("Overview", description=None, color_name="blue-70")
# KPIs
c1, c2, c3 = st.columns(3)
total_laps = int(tours['LapNumber'].max()) if not tours.empty else 0
with c1:
    st.metric("Nombre de tours", f"{total_laps}")
with c2:
    st.metric("Nombre de pilotes au départ", f"{len(pilotes)}")
with c3:
    st.metric("Grand-Prix", nom_gp)

add_vertical_space(1)
# Meilleur tour de la session
colored_header("Meilleur tour de la session", description=None, color_name="blue-70")
if 'LapTime' in tours and tours['LapTime'].notna().any():
    best_idx = tours['LapTime'].idxmin()
    best_row = tours.loc[best_idx]
    bcol1, bcol2, bcol3 = st.columns(3)
    with bcol1:
        st.metric("Pilote", str(best_row.get('Driver', '')))
    with bcol2:
        st.metric("Tour", int(best_row.get('LapNumber', 0)))
    with bcol3:
        st.metric("Temps", formatage_timedelta(best_row.get('LapTime')))
else:
    st.info("Meilleur tour indisponible.")


# Top 10 meilleurs tours
colored_header("Chronos — Top 10 meilleurs tours", description=None, color_name="blue-70")
if not tours.empty and 'LapTime' in tours:
    top = (tours.sort_values('LapTime')
                .loc[tours['LapTime'].notna(),
                     ['Driver','LapNumber','LapTime','LapSeconds','Compound','Stint']]
                .head(10))

    top = pd.DataFrame(top).copy()
    top['LapTimeStr'] = top['LapTime'].apply(formatage_timedelta)
    top_display = top[['Driver','LapNumber','LapTimeStr','Compound','Stint']]
    st.dataframe(top_display, width="stretch")
else:
    st.info("Pas de données de tours.")

add_vertical_space(1)
# Répartition des pneus
colored_header("Répartition des composés pneus", description=None, color_name="blue-70")
if 'Compound' in tours:
    comp = (tours.dropna(subset=['Compound'])
                .groupby(['Driver','Compound']).size()
                .reset_index(name='Tours'))
    # Ordre et couleurs fixes : un composé garde la même teinte d'une session
    # à l'autre, même si certains composés sont absents.
    presents = [c for c in ORDRE_COMPOSES if c in set(comp['Compound'])]
    autres = sorted(set(comp['Compound']) - set(ORDRE_COMPOSES))
    fig = px.bar(
        comp, x='Driver', y='Tours', color='Compound', barmode='stack',
        category_orders={'Compound': presents + autres},
        color_discrete_map=COMPOSES,
        labels={'Tours': 'Tours', 'Driver': 'Pilote', 'Compound': 'Composé'},
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Pas d'information pneus disponible.")

add_vertical_space(1)
colored_header("Résultats de la course", description="Résultats officiels si disponibles", color_name="blue-70")
if not resultats.empty:
    cols = [c for c in ["Position","BroadcastName","DriverNumber","TeamName","Points","Status","Time","FastestLapTime"] if c in resultats.columns]
    res = resultats[cols].copy()
    res = pd.DataFrame(res).copy()
    for c in ["Time","FastestLapTime"]:
        if c in res.columns:
            try:
                res[c] = res[c].apply(formatage_timedelta)
            except Exception:
                pass
    st.markdown("Résultats officiels **(si disponibles)**")
    st.dataframe(res, width="stretch")
else:
    st.info("Résultats non disponibles pour cette session.")
