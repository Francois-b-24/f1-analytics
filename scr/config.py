import streamlit as st
import fastf1
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.metric_cards import style_metric_cards

def configure_page_home(title: str = "F1 Analytics", page_icon: str = "🏎️", menu_items: dict | None = None):
    fastf1.Cache.enable_cache('cache')
    st.set_page_config(
        page_title=title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items=menu_items,
    )

def configure_page(title: str = "F1 Analytics", page_icon: str = "📊", menu_items: dict | None = None):
    fastf1.Cache.enable_cache('cache')
    st.set_page_config(
        page_title=title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items=menu_items,
    )

def section_header(title: str, description: str | None = None, color_name: str = "blue-70"):
    """En-tête coloré pratique pour garder un style cohérent sur toutes les pages."""
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
    """Applique un style uniforme aux cartes de métriques Streamlit dans toute l'application."""
    style_metric_cards(
        background_color=background_color,
        border_color=border_color,
        border_left_color=border_left_color,
        border_radius=border_radius,
        box_shadow=box_shadow,
    )
