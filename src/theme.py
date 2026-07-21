"""Thème de visualisation partagé — Plotly et matplotlib.

Centralise les couleurs des graphiques pour qu'ils s'accordent au thème clair
de l'application (`f1_theme.css`) au lieu d'utiliser les couleurs par défaut
de Plotly.

Ce module est la **source de vérité des couleurs** : `src.data` importe ces
constantes pour ses figures matplotlib plutôt que de porter ses propres valeurs.
Changer de thème ne demande donc de toucher qu'ici, à `f1_theme.css` et à
`.streamlit/config.toml`.

Palette catégorielle
--------------------
Les couleurs de séries ne sont pas choisies à l'œil : la palette est validée
(bande de luminosité, plancher de chroma, séparation pour les daltonismes
protan/deutan, contraste sur la surface #f7f8fa).

Un mode clair se choisit, il ne se déduit pas d'une inversion du mode sombre :
les teintes calibrées pour un fond sombre passent sous le seuil de contraste
sur fond clair. Les accents d'interface (`ACCENT_GOLD`, `ACCENT_BLUE`) ne
conviennent PAS comme couleurs de données et restent réservés au chrome
(titres, bordures, curseurs).

L'ordre des créneaux est le mécanisme de sécurité daltonisme : il ne doit pas
être modifié, et les couleurs sont attribuées dans l'ordre, jamais en cycle.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# --- Surfaces et encres (alignées sur f1_theme.css) ------------------------
SURFACE = "#f7f8fa"       # --bg-base : gris très clair, légèrement froid
SURFACE_ALT = "#ffffff"   # --bg-surface : cartes et sidebar, en relief
INK_PRIMARY = "#111418"   # --text-primary (17.4:1 sur la surface)
INK_SECONDARY = "#5b6470" # --text-secondary (5.6:1)
GRID = "#e4e7eb"          # --border-subtle : grille discrète
AXIS = "#c8cdd4"          # --border-default : axes et bordures

# Fond de piste des cartes du circuit (cartographie). Volontairement plus
# sombre que les axes : c'est le décor sur lequel repose le tracé coloré, et
# il doit contraster avec les DEUX extrémités de la colormap. Mesuré sur ce
# gris, plasma tient à 4.2:1 côté jaune et 3.1:1 côté violet — un gris plus
# clair rendait les hautes vitesses illisibles.
FOND_PISTE = "#6b7280"

# --- Accents de marque (chrome uniquement, pas des couleurs de séries) -----
# Le rouge de la marque passe le contraste sur fond clair (5.25:1) et est
# conservé tel quel. L'or et le bleu du thème sombre y tombaient à 2.1 et
# 2.4:1 : ils sont assombris pour rester lisibles.
ACCENT_RED = "#c1322d"    # 5.25:1 — identité conservée
ACCENT_GOLD = "#8a6d20"   # 4.61:1 (était #c9a961, illisible sur clair)
ACCENT_BLUE = "#1f6feb"   # 4.36:1 (était #58a6ff)

# --- Palette catégorielle validée pour le fond clair -----------------------
# Vérifiée sur #f7f8fa : bande L 0.43–0.77, chroma ≥ 0.1, pire paire adjacente
# ΔE 9.1 (protan) et 19.6 (vision normale) — tous PASS.
# Trois créneaux (magenta, jaune, aqua) sont sous 3:1 de contraste : admis car
# l'encodage secondaire est toujours présent (légende nommée, étiquettes).
CATEGORIQUE: tuple[str, ...] = (
    "#2a78d6",  # bleu
    "#008300",  # vert
    "#e87ba4",  # magenta
    "#eda100",  # jaune
    "#1baf7a",  # aqua
    "#eb6834",  # orange
    "#4a3aa7",  # violet
    "#e34948",  # rouge
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
# Validé sur #f7f8fa : bande L, chroma et plancher vision normale (pire paire
# ΔE 20.8) tous PASS. La séparation daltonisme de la paire aqua/rouge tombe
# dans la bande plancher (6.9), admis car l'encodage secondaire est présent :
# légende nommée et espace entre segments empilés.
COMPOSES: dict[str, str] = {
    "HARD": "#2a78d6",          # bleu
    "MEDIUM": "#eda100",        # jaune
    "SOFT": "#e34948",          # rouge
    "INTERMEDIATE": "#1baf7a",  # aqua
    "WET": "#4a3aa7",           # violet
    "UNKNOWN": INK_SECONDARY,
}

# Ordre d'affichage stable, du plus dur au plus tendre puis pneus pluie.
ORDRE_COMPOSES: tuple[str, ...] = (
    "HARD", "MEDIUM", "SOFT", "INTERMEDIATE", "WET", "UNKNOWN",
)


# --- Paires sémantiques ----------------------------------------------------
# Freinage / traction : le rouge de la marque associé à ce vert passe TOUS les
# contrôles sans aucun WARN sur fond clair (ΔE 9.5 en deutéranopie, 29.9 en
# vision normale, contraste ≥ 3:1). La même paire tenait sur fond sombre :
# elle est valable dans les deux modes, donc inchangée.
FREINAGE = ACCENT_RED
TRACTION = "#199e70"

# Échelle séquentielle (magnitude) : une seule teinte, clair → foncé.
SEQUENTIELLE = "Blues"
# Échelle divergente (polarité autour d'une référence), midpoint neutre.
DIVERGENTE = "RdBu"

_TEMPLATE_NOM = "f1_light"


def _construire_template() -> go.layout.Template:
    """Construit le template Plotly clair de l'application."""
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
