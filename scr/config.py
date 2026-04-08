import logging
from pathlib import Path

import streamlit as st
import fastf1
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.metric_cards import style_metric_cards

# Racine du projet (parent de scr/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CSS_PATH = _PROJECT_ROOT / "f1_theme.css"
_CACHE_DIR = _PROJECT_ROOT / "cache"

logger = logging.getLogger("f1_analytics")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _enable_fastf1_cache() -> None:
    """Active le cache FastF1 une seule fois par process."""
    if getattr(_enable_fastf1_cache, "_done", False):
        return
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(_CACHE_DIR))
        _enable_fastf1_cache._done = True  # type: ignore[attr-defined]
    except Exception as exc:
        logger.warning("Impossible d'activer le cache FastF1: %s", exc)


def load_theme_css() -> None:
    """Charge la feuille de style f1_theme.css via un chemin absolu, silencieux si absent."""
    try:
        css = _CSS_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        logger.warning("Fichier CSS introuvable: %s", _CSS_PATH)
    except Exception as exc:
        logger.warning("Erreur chargement CSS: %s", exc)


def configure_page_home(title: str = "F1 Analytics", page_icon: str = "🏎️", menu_items: dict | None = None):
    """
    Configure la page d'accueil Streamlit avec le cache FastF1 activé et le thème CSS chargé.
    """
    _enable_fastf1_cache()
    st.set_page_config(
        page_title=title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items=menu_items,
    )
    load_theme_css()


def configure_page(title: str = "F1 Analytics", page_icon: str = "📊", menu_items: dict | None = None):
    """
    Configure une page Streamlit secondaire avec cache FastF1 et thème CSS.
    """
    _enable_fastf1_cache()
    st.set_page_config(
        page_title=title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items=menu_items,
    )
    load_theme_css()


def section_header(title: str, description: str | None = None, color_name: str = "blue-70"):
    """Affiche un en-tête coloré pour garder un style cohérent sur toutes les pages."""
    colored_header(title, description=description, color_name=color_name)


def spacer(lines: int = 1):
    """Ajoute un espace vertical entre les sections."""
    add_vertical_space(lines)


def style_kpis(
    background_color: str = "#0E1117",
    border_color: str = "#2B313E",
    border_left_color: str = "#00D4FF",
    border_radius: int = 8,
    box_shadow: bool = True,
):
    """Applique un style uniforme aux cartes de métriques Streamlit (legacy, remplacé par le thème CSS)."""
    style_metric_cards(
        background_color=background_color,
        border_color=border_color,
        border_left_color=border_left_color,
        border_radius=border_radius,
        box_shadow=box_shadow,
    )
