import streamlit as st
import fastf1
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.metric_cards import style_metric_cards

def configure_page_home(title: str = "F1 Analytics", page_icon: str = "🏎️", menu_items: dict | None = None):
    """
    Configure la page d'accueil Streamlit avec le cache FastF1 activé.
    
    Paramètres
    ----------
    title : str, optionnel
        Titre de la page (par défaut "F1 Analytics").
    page_icon : str, optionnel
        Icône de la page (par défaut "🏎️").
    menu_items : dict | None, optionnel
        Items du menu Streamlit personnalisés.
    """
    fastf1.Cache.enable_cache('cache')
    st.set_page_config(
        page_title=title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items=menu_items,
    )

def configure_page(title: str = "F1 Analytics", page_icon: str = "📊", menu_items: dict | None = None):
    """
    Configure une page Streamlit avec le cache FastF1 activé.
    
    Paramètres
    ----------
    title : str, optionnel
        Titre de la page (par défaut "F1 Analytics").
    page_icon : str, optionnel
        Icône de la page (par défaut "📊").
    menu_items : dict | None, optionnel
        Items du menu Streamlit personnalisés.
    """
    fastf1.Cache.enable_cache('cache')
    st.set_page_config(
        page_title=title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items=menu_items,
    )

def section_header(title: str, description: str | None = None, color_name: str = "blue-70"):
    """
    Affiche un en-tête coloré pour garder un style cohérent sur toutes les pages.
    
    Paramètres
    ----------
    title : str
        Titre de la section.
    description : str | None, optionnel
        Description optionnelle sous le titre.
    color_name : str, optionnel
        Nom de la couleur du thème (par défaut "blue-70").
    """
    colored_header(title, description=description, color_name=color_name)

def spacer(lines: int = 1):
    """
    Ajoute un espace vertical entre les sections.
    
    Paramètres
    ----------
    lines : int, optionnel
        Nombre de lignes d'espace à ajouter (par défaut 1).
    """
    add_vertical_space(lines)

def style_kpis(
    background_color: str = "#0E1117",
    border_color: str = "#2B313E",
    border_left_color: str = "#00D4FF",
    border_radius: int = 8,
    box_shadow: bool = True,
):
    """
    Applique un style uniforme aux cartes de métriques Streamlit.
    
    Note: Cette fonction est maintenant remplacée par le thème CSS adaptatif.
    Conservée pour compatibilité.
    
    Paramètres
    ----------
    background_color : str, optionnel
        Couleur de fond des cartes.
    border_color : str, optionnel
        Couleur de la bordure.
    border_left_color : str, optionnel
        Couleur de la bordure gauche (accent).
    border_radius : int, optionnel
        Rayon des coins arrondis.
    box_shadow : bool, optionnel
        Activer l'ombre portée.
    """
    style_metric_cards(
        background_color=background_color,
        border_color=border_color,
        border_left_color=border_left_color,
        border_radius=border_radius,
        box_shadow=box_shadow,
    )
