"""Montage de l'application : navigation, barre latérale, rendu.

Ce module est importé — jamais exécuté par `runpy` — par les deux points
d'entrée (`Home.py` et `streamlit_app.py`). Les modules du paquet `src` ne
sont donc importés qu'une fois, dans un seul contexte : `runpy.run_path`
créait un module `__main__` distinct, et la réimportation qui s'ensuivait
levait `ImportError` en production.
"""
import streamlit as st

from .accueil import rendre as rendre_accueil
from .config import configure_page_home
from .navigation import construire_pages
from .ui import selecteur_session_global


def demarrer() -> None:
    """Configure la page, monte la navigation et rend la page courante."""
    configure_page_home("F1 Analytics")

    pages = st.navigation(construire_pages(rendre_accueil))

    # Rendu ici, et nulle part ailleurs : la barre latérale appartient au
    # routeur, donc le sélecteur existe sur toutes les pages et ses clés ne
    # peuvent pas être rendues deux fois dans un même run
    # (`StreamlitDuplicateElementKey`). Avant `.run()` pour que la page lise
    # une sélection déjà à jour.
    selecteur_session_global()

    pages.run()
