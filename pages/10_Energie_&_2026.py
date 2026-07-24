import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_extras.colored_header import colored_header

from src.analytics import (
    DEPLOY_TAPER_END_KMH,
    DEPLOY_TAPER_START_KMH,
    comparaison_proxys_energie,
    phases_telemetrie,
    resume_proxys_energie,
)
from src.config import configure_page
from src.data import chargement_session, telemetrie_pilote
from src.theme import ACCENT_BLUE, ACCENT_GOLD, ACCENT_RED, FREINAGE, TRACTION
from src.ui import selections_courantes

configure_page("F1 Analytics – Énergie & 2026", page_icon="⚡")

st.subheader("⚡ Énergie & réglementation 2026")
st.caption(
    "Lecture du comportement énergétique d'un tour à partir de la télémétrie publiée."
)

# ---------------------------------------------------------------------------
# Avertissement méthodologique — affiché avant toute donnée, volontairement.
# ---------------------------------------------------------------------------
st.warning(
    "**Ces indicateurs sont des estimations, pas des mesures.** "
    "La Formule 1 ne publie aucune donnée d'énergie : état de charge de la batterie, "
    "taux de déploiement et de récupération du MGU-K, mode d'aéro active. "
    "Tout ce qui suit est **dérivé** des seuls canaux réellement diffusés "
    "(vitesse, accélérateur, frein) et doit être lu comme un indice de comportement, "
    "sans vérité terrain pour le valider."
)

with st.expander("📘 Ce qui change en 2026 — et pourquoi la donnée brute manque"):
    st.markdown(
        f"""
**La réglementation 2026** rééquilibre l'unité de puissance autour de ~50 % d'énergie
électrique :

- **MGU-K porté à 350 kW** (contre 120 kW auparavant), le MGU-H disparaît.
- **Récupération plafonnée à ~7 MJ par tour** (abaissée de 8 à 7 MJ en avril 2026
  pour limiter la récupération excessive).
- **Décroissance du déploiement** : la puissance électrique décroît à partir de
  **{DEPLOY_TAPER_START_KMH:.0f} km/h** et s'annule à **{DEPLOY_TAPER_END_KMH:.0f} km/h**.
- **Override MGU-K** : le poursuivant peut réclamer un surcroît d'énergie pour attaquer.
- **Aéro active** : mode X (faible traînée, ligne droite) et mode Z (appui, virage),
  en remplacement du DRS.

**Pourquoi ces valeurs ne sont pas affichées ici ?** Parce qu'elles ne sont
diffusées nulle part. Le mainteneur de FastF1 l'a confirmé :
*« F1 has decided to not make any data on active aero and ERS state available
publicly »*. Les données d'aéro active ont même été testées durant les essais
de pré-saison, puis **retirées du flux**.

La télémétrie publique se limite donc à : vitesse, régime moteur, rapport engagé,
accélérateur, frein, position. C'est à partir de ces canaux — et d'eux seuls —
que les indicateurs ci-dessous sont construits.
"""
    )

annee, grand_prix, session_type, loaded = selections_courantes(required=True)
if not loaded:
    st.info("Charge d'abord une session depuis la page Home.")
    st.stop()

data = chargement_session(annee, grand_prix, session_type)
pilotes = data["pilotes"]
best_laps = data.get("best_laps", {})

if not best_laps:
    st.info(
        "⏳ Télémétrie indisponible pour cette session. "
        "Les données sont publiées avec un délai de 24–48 h après la course. "
        "Réessaie plus tard, ou sélectionne une session plus ancienne."
    )
    st.stop()

# Pilotes ayant un meilleur tour exploitable ; la télémétrie elle-même est
# chargée à la demande, pilote par pilote.
dispo = [p for p in pilotes if p in best_laps]
if not dispo:
    st.info("Aucun pilote avec télémétrie exploitable sur cette session.")
    st.stop()

pilote = st.selectbox("Pilote analysé", dispo, key="energie_pilote")
with st.spinner(f"Chargement de la télémétrie de {pilote}…"):
    tel = telemetrie_pilote(data, pilote)

if tel is None or tel.empty:
    st.warning(f"Télémétrie non disponible pour {pilote}.")
    st.stop()

# ---------------------------------------------------------------------------
# Indicateurs dérivés du tour le plus rapide
# ---------------------------------------------------------------------------
colored_header(
    "Indicateurs du tour le plus rapide",
    description=f"{pilote} — estimations dérivées de la télémétrie",
    color_name="blue-70",
)

resume = resume_proxys_energie(tel)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(
        "Freinage",
        f"{resume['part_freinage'] * 100:.1f} %",
        help="Part de la distance du tour parcourue frein appuyé. Sous freinage, "
        "le MGU-K récupère de l'énergie — mais la quantité réelle n'est pas publiée.",
    )
with c2:
    st.metric(
        "Pleine charge",
        f"{resume['part_traction'] * 100:.1f} %",
        help="Part de la distance parcourue accélérateur ≥ 90 %, phases où "
        "l'énergie électrique est typiquement déployée.",
    )
with c3:
    st.metric(
        f"Au-delà de {DEPLOY_TAPER_START_KMH:.0f} km/h",
        f"{resume['part_au_dela_taper'] * 100:.1f} %",
        help="Part du tour au-delà du seuil où le déploiement MGU-K commence "
        "à décroître selon la réglementation 2026.",
    )
with c4:
    st.metric(
        "Zones de freinage",
        f"{resume['nb_freinages']}",
        help="Nombre de phases de freinage distinctes — autant de fenêtres "
        "de récupération sur un tour.",
    )

st.caption(
    "Freinage = proxy des fenêtres de **récupération** · "
    "Pleine charge = proxy des phases de **déploiement**."
)
st.caption(
    f"Tour de référence : {resume['distance_tour']:.0f} m · "
    f"vitesse maximale {resume['vitesse_max']:.0f} km/h · "
    f"{resume['distance_freinage']:.0f} m de freinage · "
    f"{resume['distance_traction']:.0f} m de pleine charge."
)

# ---------------------------------------------------------------------------
# Profil de vitesse et seuils réglementaires
# ---------------------------------------------------------------------------
colored_header(
    "Profil de vitesse et seuils de déploiement",
    description="Où le déploiement électrique décroît selon la réglementation 2026",
    color_name="blue-70",
)

if {"Distance", "Speed"}.issubset(tel.columns):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=tel["Distance"],
            y=tel["Speed"],
            mode="lines",
            name=f"Vitesse {pilote}",
            line=dict(color=ACCENT_BLUE, width=2),
        )
    )
    fig.add_hline(
        y=DEPLOY_TAPER_START_KMH,
        line=dict(color=ACCENT_GOLD, dash="dash", width=1.5),
        annotation_text=f"Début de décroissance ({DEPLOY_TAPER_START_KMH:.0f} km/h)",
        annotation_position="top left",
    )
    fig.add_hline(
        y=DEPLOY_TAPER_END_KMH,
        line=dict(color=ACCENT_RED, dash="dot", width=1.5),
        annotation_text=f"Déploiement nul ({DEPLOY_TAPER_END_KMH:.0f} km/h)",
        annotation_position="top left",
    )
    fig.update_layout(
        xaxis_title="Distance (m)",
        yaxis_title="Vitesse (km/h)",
        height=420,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "En 2026, la puissance électrique décroît au-delà de "
        f"{DEPLOY_TAPER_START_KMH:.0f} km/h. Les portions du tour situées au-dessus "
        "de la ligne dorée sont celles où le moteur thermique prend le relais."
    )
else:
    st.info("Profil de vitesse indisponible pour ce tour.")

# ---------------------------------------------------------------------------
# Découpage en phases
# ---------------------------------------------------------------------------
colored_header(
    "Phases de freinage et de traction",
    description="Fenêtres de récupération et de déploiement estimées",
    color_name="blue-70",
)

phases = phases_telemetrie(tel)
if phases.empty:
    st.info("Aucune phase exploitable détectée sur ce tour.")
else:
    fig_ph = px.bar(
        phases,
        x="Longueur",
        y="Phase",
        color="Phase",
        orientation="h",
        base="DistanceDebut",
        hover_data={
            "DistanceDebut": ":.0f",
            "DistanceFin": ":.0f",
            "Longueur": ":.0f",
            "VitesseEntree": ":.0f",
            "VitesseSortie": ":.0f",
        },
        color_discrete_map={"Freinage": FREINAGE, "Traction": TRACTION},
        labels={"Longueur": "Distance (m)", "Phase": ""},
    )
    fig_ph.update_layout(height=260, xaxis_title="Distance sur le tour (m)")
    st.plotly_chart(fig_ph, use_container_width=True)

    affichage = phases.copy()
    for col in ("DistanceDebut", "DistanceFin", "Longueur", "VitesseEntree", "VitesseSortie"):
        affichage[col] = affichage[col].round(0).astype(int)
    affichage = affichage.rename(
        columns={
            "DistanceDebut": "Début (m)",
            "DistanceFin": "Fin (m)",
            "Longueur": "Longueur (m)",
            "VitesseEntree": "V. entrée (km/h)",
            "VitesseSortie": "V. sortie (km/h)",
        }
    )
    st.dataframe(affichage, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Comparaison entre pilotes
# ---------------------------------------------------------------------------
colored_header(
    "Comparaison entre pilotes",
    description="Styles de pilotage au prisme des proxys énergétiques",
    color_name="blue-70",
)

# Défaut restreint à 4 pilotes : chaque pilote comparé nécessite une requête
# de télémétrie à la demande, donc un défaut trop large rallongerait l'ouverture
# de la page. L'utilisateur peut en ajouter, chacun se chargeant à la volée.
defaut = dispo[: min(4, len(dispo))]
selection = st.multiselect(
    "Pilotes à comparer",
    options=dispo,
    default=defaut,
    key="energie_drivers",
)

if not selection:
    st.info("Sélectionne au moins un pilote.")
else:
    # Télémétrie chargée à la demande pour les seuls pilotes comparés.
    with st.spinner("Chargement de la télémétrie des pilotes comparés…"):
        tel_selection = {
            p: t for p in selection
            if not (t := telemetrie_pilote(data, p)).empty
        }
    comparaison = comparaison_proxys_energie(tel_selection, pilotes=selection)
    if comparaison.empty:
        st.info("Données insuffisantes pour la comparaison.")
    else:
        fig_cmp = px.bar(
            comparaison,
            x="Pilote",
            y=["part_freinage", "part_traction"],
            barmode="group",
            labels={"value": "Part du tour", "variable": "Phase"},
            color_discrete_map={
                "part_freinage": FREINAGE,
                "part_traction": TRACTION,
            },
        )
        fig_cmp.update_layout(height=400, yaxis_tickformat=".0%")
        newnames = {"part_freinage": "Freinage", "part_traction": "Pleine charge"}
        fig_cmp.for_each_trace(lambda t: t.update(name=newnames.get(t.name, t.name)))
        st.plotly_chart(fig_cmp, use_container_width=True)

        tableau = comparaison[
            ["Pilote", "part_freinage", "part_traction", "part_au_dela_taper",
             "nb_freinages", "vitesse_max"]
        ].copy()
        for col in ("part_freinage", "part_traction", "part_au_dela_taper"):
            tableau[col] = (tableau[col] * 100).round(1)
        tableau["vitesse_max"] = tableau["vitesse_max"].round(0).astype(int)
        tableau = tableau.rename(
            columns={
                "part_freinage": "Freinage (%)",
                "part_traction": "Pleine charge (%)",
                "part_au_dela_taper": f"> {DEPLOY_TAPER_START_KMH:.0f} km/h (%)",
                "nb_freinages": "Zones de freinage",
                "vitesse_max": "V. max (km/h)",
            }
        )
        st.dataframe(tableau, use_container_width=True, hide_index=True)

st.caption(
    "⚠️ Rappel : aucune de ces valeurs ne provient d'une mesure d'énergie. "
    "Ce sont des indicateurs de comportement calculés à partir de la vitesse, "
    "de l'accélérateur et du frein."
)
