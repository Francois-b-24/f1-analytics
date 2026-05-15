import logging
import os
import tempfile
from pathlib import Path

import streamlit as st
import fastf1
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.metric_cards import style_metric_cards

# Racine du projet (parent de src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CSS_PATH = _PROJECT_ROOT / "f1_theme.css"

# Cache FastF1 hors-repo. Priorité :
#   1. variable d'environnement FASTF1_CACHE (Docker, CI)
#   2. /tmp/fastf1_cache (Streamlit Cloud — FS éphémère mais survit au process)
_CACHE_DIR = Path(os.environ.get("FASTF1_CACHE") or (Path(tempfile.gettempdir()) / "fastf1_cache"))

# --- Logging centralisé ---
_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("f1_analytics")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(_LOG_LEVEL)
    logger.propagate = False


def _init_sentry() -> None:
    """Initialise Sentry si un DSN est fourni via st.secrets ou env var.

    Idempotent — appelé une seule fois par process.
    """
    if getattr(_init_sentry, "_done", False):
        return
    dsn = None
    try:
        if hasattr(st, "secrets") and "SENTRY_DSN" in st.secrets:
            dsn = st.secrets["SENTRY_DSN"]
    except Exception:
        pass
    if not dsn:
        dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        _init_sentry._done = True  # type: ignore[attr-defined]
        return
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            environment=os.environ.get("ENV", "prod"),
            release=os.environ.get("APP_VERSION"),
        )
        logger.info("Sentry initialisé (env=%s)", os.environ.get("ENV", "prod"))
    except Exception as exc:
        logger.warning("Échec init Sentry: %s", exc)
    _init_sentry._done = True  # type: ignore[attr-defined]


def _enable_fastf1_cache() -> None:
    """Active le cache FastF1 une seule fois par process."""
    if getattr(_enable_fastf1_cache, "_done", False):
        return
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(_CACHE_DIR))
        logger.info("Cache FastF1 actif: %s", _CACHE_DIR)
        _enable_fastf1_cache._done = True  # type: ignore[attr-defined]
    except Exception as exc:
        logger.warning("Impossible d'activer le cache FastF1 (%s): %s", _CACHE_DIR, exc)


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
    _init_sentry()
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
    _init_sentry()
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
