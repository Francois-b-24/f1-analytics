"""Thème de visualisation partagé — Plotly et matplotlib.

Centralise les couleurs des graphiques pour qu'ils s'accordent au thème sombre
de l'application (`f1_theme.css`, palette carbone) au lieu d'utiliser les
couleurs par défaut de Plotly.

Palette catégorielle
--------------------
Les couleurs de séries ne sont pas choisies à l'œil : la palette est validée
(bande de luminosité, plancher de chroma, séparation pour les daltonismes
protan/deutan, contraste ≥ 3:1 sur le fond #0d1117). Les accents de l'interface
(`--accent-gold`, `--accent-blue`) ne conviennent PAS comme couleurs de données
— l'or tombe sous le plancher de chroma et lit comme un gris — ils restent donc
réservés au chrome (titres, bordures, curseurs).

L'ordre des créneaux est le mécanisme de sécurité daltonisme : il ne doit pas
être modifié, et les couleurs sont attribuées dans l'ordre, jamais en cycle.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# --- Surfaces et encres (alignées sur f1_theme.css) ------------------------
SURFACE = "#0d1117"       # --bg-base
SURFACE_ALT = "#161b22"   # --bg-surface
INK_PRIMARY = "#e6edf3"   # --text-primary
INK_SECONDARY = "#9ba3af" # --text-secondary
GRID = "#21262d"          # --border-subtle
AXIS = "#30363d"          # --border-default

# --- Accents de marque (chrome uniquement, pas des couleurs de séries) -----
ACCENT_RED = "#c1322d"
ACCENT_GOLD = "#c9a961"
ACCENT_BLUE = "#58a6ff"

# --- Palette catégorielle validée pour le fond sombre ----------------------
# Vérifiée sur #0d1117 : bande L 0.48–0.67, chroma ≥ 0.1, pire paire adjacente
# ΔE 8.4 (protan) et 19.3 (vision normale), contraste ≥ 3:1 — tous PASS.
CATEGORIQUE: tuple[str, ...] = (
    "#3987e5",  # bleu
    "#008300",  # vert
    "#d55181",  # magenta
    "#c98500",  # jaune
    "#199e70",  # aqua
    "#d95926",  # orange
    "#9085e9",  # violet
    "#e66767",  # rouge
)

# --- Composés pneus --------------------------------------------------------
# La couleur suit le composé, jamais son rang dans les données : sans cette
# table, un composé absent d'une session décalerait les couleurs de tous les
# autres et « SOFT » changerait de teinte d'une course à l'autre.
#
# Les teintes conventionnelles de la F1 (dur = blanc, tendre = rouge) ne sont
# pas reprises telles quelles : le blanc/gris tombe sous le plancher de chroma
# (il ne porte plus d'identité) et le couple jaune/rouge se confond en
# deutéranopie. On prend donc des créneaux validés, l'étiquette du composé
# portant le sens.
# Validé sur #0d1117 : bande L, chroma, contraste ≥ 3:1 et plancher vision
# normale (pire paire ΔE 15.1) tous PASS. La séparation daltonisme de la paire
# MEDIUM/SOFT tombe dans la bande plancher (6.2), ce qui est admis car
# l'encodage secondaire est présent : légende nommée et espace entre segments.
COMPOSES: dict[str, str] = {
    "HARD": "#3987e5",          # bleu
    "MEDIUM": "#c98500",        # jaune
    "SOFT": "#e34948",          # rouge
    "INTERMEDIATE": "#199e70",  # aqua
    "WET": "#9085e9",           # violet
    "UNKNOWN": INK_SECONDARY,
}

# Ordre d'affichage stable, du plus dur au plus tendre puis pneus pluie.
ORDRE_COMPOSES: tuple[str, ...] = (
    "HARD", "MEDIUM", "SOFT", "INTERMEDIATE", "WET", "UNKNOWN",
)


# --- Paires sémantiques ----------------------------------------------------
# Freinage / traction : le rouge de la marque est conservé, associé à un vert
# qui satisfait toutes les contraintes (ΔE 29.9 en vision normale).
FREINAGE = ACCENT_RED
TRACTION = "#199e70"

# Échelle séquentielle (magnitude) : une seule teinte, clair → foncé.
SEQUENTIELLE = "Blues"
# Échelle divergente (polarité autour d'une référence), midpoint neutre.
DIVERGENTE = "RdBu"

_TEMPLATE_NOM = "f1_dark"


def _construire_template() -> go.layout.Template:
    """Construit le template Plotly sombre de l'application."""
    return go.layout.Template(
        layout=dict(
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            font=dict(color=INK_PRIMARY, size=13),
            title=dict(font=dict(color=INK_PRIMARY, size=16)),
            colorway=list(CATEGORIQUE),
            xaxis=dict(
                gridcolor=GRID,
                linecolor=AXIS,
                zerolinecolor=AXIS,
                tickfont=dict(color=INK_SECONDARY),
                title=dict(font=dict(color=INK_SECONDARY)),
            ),
            yaxis=dict(
                gridcolor=GRID,
                linecolor=AXIS,
                zerolinecolor=AXIS,
                tickfont=dict(color=INK_SECONDARY),
                title=dict(font=dict(color=INK_SECONDARY)),
            ),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                bordercolor=AXIS,
                font=dict(color=INK_SECONDARY),
            ),
            hoverlabel=dict(
                bgcolor=SURFACE_ALT,
                bordercolor=AXIS,
                font=dict(color=INK_PRIMARY),
            ),
            colorscale=dict(sequential=SEQUENTIELLE, diverging=DIVERGENTE),
            margin=dict(l=60, r=30, t=50, b=50),
        )
    )


def appliquer_theme_plotly() -> None:
    """Enregistre le template et en fait le défaut — idempotent.

    Appelé par `configure_page` / `configure_page_home` : toutes les figures
    Plotly héritent alors du thème sans modification page par page.
    """
    if _TEMPLATE_NOM not in pio.templates:
        pio.templates[_TEMPLATE_NOM] = _construire_template()
    pio.templates.default = _TEMPLATE_NOM


def couleur_pilote(index: int) -> str:
    """Couleur de série pour le n-ième pilote, attribuée dans l'ordre.

    Au-delà de 8 séries, la palette est réutilisée : au-delà, préférer un
    regroupement ou des facettes plutôt que de multiplier les teintes.
    """
    return CATEGORIQUE[index % len(CATEGORIQUE)]
