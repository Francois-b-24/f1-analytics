"""Rendu de la page d'accueil.

Pourquoi un module, et plus un script à double rôle
---------------------------------------------------
`Home.py` cumulait deux rôles : point d'entrée délégant au routeur par
`runpy.run_path`, et page rendue par ce même routeur. En production, où il est
le fichier d'entrée, il était donc le premier à importer `src.ui` **et** était
relancé par `runpy` au milieu de cet import. `src.ui` n'étant que partiellement
initialisé au second passage, l'accueil levait `ImportError` sur un symbole
importé, puis `AttributeError` sur un attribut du module — deux pannes
invisibles en local comme en CI, où l'ordre d'import diffère.

Le rendu vit désormais ici, importé normalement par le routeur : plus de
`runpy`, plus de réentrance, plus de dépendance à l'ordre d'initialisation.
`Home.py` subsiste comme point d'entrée mince, le « Main file path » étant
configuré chez l'hébergeur, hors du dépôt.
"""
import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from .data import chargement_session
from .theme import COMPOSES, ORDRE_COMPOSES
from .ui import barre_contexte, selections_courantes
from .utils import formatage_timedelta

_logger = logging.getLogger("f1_analytics.accueil")


def _entete() -> None:
    """Titre animé, citation et accroche — l'identité visuelle de l'app."""
    st.markdown(
        """
        <div style="text-align:center; font-size: 1.5em; font-weight: 500;">
            <span class="f1-glow"><span class="f1-car-emoji">🏎️</span> F1 Analytics</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="citation" style="text-align:center;font-size:1.1em;'
        'padding-top:0.7em;padding-bottom:0.5em;">'
        '« STILL I RISE » <span style="font-size:0.85em;">– Lewis Hamilton</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Explorez un week-end de Grand Prix : chronos, télémétrie, pneus, "
        "arrêts, météo. Choisissez la session dans la barre latérale ; les "
        "pages sont groupées par thème juste au-dessus."
    )
    barre_contexte()


def _afficher_erreur(exc: Exception, annee, grand_prix, session_type) -> None:
    """Message d'erreur orienté cause probable, puis détails techniques."""
    _logger.exception("Échec chargement session %s / %s / %s",
                      annee, grand_prix, session_type)
    err_type = type(exc).__name__
    msg = str(exc) or "(pas de message)"
    bas = msg.lower()

    if "404" in msg or "not found" in bas or "no data" in bas:
        st.error(
            f"❌ Session indisponible : {annee} – {grand_prix} "
            f"({session_type}). Cette session n'a pas encore eu lieu ou n'est "
            f"pas publiée."
        )
    elif "connection" in bas or "timeout" in bas or err_type in ("ConnectionError", "Timeout"):
        st.error("🔌 Problème de connexion à l'API F1. Réessaie dans quelques instants.")
    else:
        st.error(f"⚠️ Impossible de charger cette session : **{err_type}** — {msg}")

    col_a, _ = st.columns([1, 4])
    with col_a:
        if st.button("🔄 Réessayer", key="retry_load"):
            chargement_session.clear()
            st.rerun()
    with st.expander("Détails techniques"):
        import traceback

        st.code(f"{err_type}: {msg}\n\n{traceback.format_exc()}")


def rendre() -> None:
    """Rend l'accueil : vue d'ensemble, meilleurs tours, pneus, résultats."""
    _entete()

    # Le sélecteur de session vit dans le routeur, donc dans la barre latérale
    # de toutes les pages. Le rendre aussi ici dupliquerait ses clés dans le
    # même run et lèverait `StreamlitDuplicateElementKey`.
    annee, grand_prix, session_type, loaded = selections_courantes(required=False)

    if not loaded:
        st.info(
            "Choisissez une saison, un Grand Prix et un type de session dans "
            "la barre latérale, puis **Charger**."
        )
        return

    try:
        data = chargement_session(annee, grand_prix, session_type)
    except Exception as exc:  # noqa: BLE001 — message adapté puis sortie propre
        _afficher_erreur(exc, annee, grand_prix, session_type)
        return

    tours = data["tours"]
    pilotes = data["pilotes"]
    resultats = data["resultats"]

    st.markdown("### Overview")
    c1, c2, c3 = st.columns(3)
    total_laps = int(tours["LapNumber"].max()) if not tours.empty else 0
    with c1:
        st.metric("Nombre de tours", f"{total_laps}")
    with c2:
        st.metric("Nombre de pilotes au départ", f"{len(pilotes)}")
    with c3:
        st.metric("Grand-Prix", grand_prix)

    st.write("")
    st.markdown("### Meilleur tour de la session")
    if "LapTime" in tours and tours["LapTime"].notna().any():
        meilleur = tours.loc[tours["LapTime"].idxmin()]
        b1, b2, b3 = st.columns(3)
        with b1:
            st.metric("Pilote", str(meilleur.get("Driver", "")))
        with b2:
            st.metric("Tour", int(meilleur.get("LapNumber", 0)))
        with b3:
            st.metric("Temps", formatage_timedelta(meilleur.get("LapTime")))
    else:
        st.info("Meilleur tour indisponible.")

    st.markdown("### Chronos — Top 10 meilleurs tours")
    if not tours.empty and "LapTime" in tours:
        top = (tours.sort_values("LapTime")
                    .loc[tours["LapTime"].notna(),
                         ["Driver", "LapNumber", "LapTime", "LapSeconds", "Compound", "Stint"]]
                    .head(10))
        top = pd.DataFrame(top).copy()
        top["LapTimeStr"] = top["LapTime"].apply(formatage_timedelta)
        st.dataframe(
            top[["Driver", "LapNumber", "LapTimeStr", "Compound", "Stint"]],
            width="stretch",
        )
    else:
        st.info("Pas de données de tours.")

    st.write("")
    st.markdown("### Répartition des composés pneus")
    if "Compound" in tours:
        comp = (tours.dropna(subset=["Compound"])
                     .groupby(["Driver", "Compound"]).size()
                     .reset_index(name="Tours"))
        # Ordre et couleurs fixes : un composé garde la même teinte d'une
        # session à l'autre, même si certains composés sont absents.
        presents = [c for c in ORDRE_COMPOSES if c in set(comp["Compound"])]
        autres = sorted(set(comp["Compound"]) - set(ORDRE_COMPOSES))
        fig = px.bar(
            comp, x="Driver", y="Tours", color="Compound", barmode="stack",
            category_orders={"Compound": presents + autres},
            color_discrete_map=COMPOSES,
            labels={"Tours": "Tours", "Driver": "Pilote", "Compound": "Composé"},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas d'information pneus disponible.")

    st.write("")
    st.markdown("### Résultats de la course")
    st.caption("Résultats officiels si disponibles")
    if not resultats.empty:
        colonnes = [c for c in ("Position", "BroadcastName", "DriverNumber",
                                "TeamName", "Points", "Status", "Time",
                                "FastestLapTime") if c in resultats.columns]
        res = pd.DataFrame(resultats[colonnes]).copy()
        for c in ("Time", "FastestLapTime"):
            if c in res.columns:
                try:
                    res[c] = res[c].apply(formatage_timedelta)
                except Exception:  # noqa: BLE001 — colonne non convertible, affichée brute
                    pass
        st.dataframe(res, width="stretch")
    else:
        st.info("Résultats non disponibles pour cette session.")
