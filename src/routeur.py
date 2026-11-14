"""Montage de l'application : navigation, barre latérale, rendu.

Ce module est importé — jamais exécuté par `runpy` — par les deux points
d'entrée (`Home.py` et `streamlit_app.py`). Les modules du paquet `src` ne
sont donc importés qu'une fois, dans un seul contexte : `runpy.run_path`
créait un module `__main__` distinct, et la réimportation qui s'ensuivait
levait `ImportError` en production.
"""
import streamlit as st

from .config import configure_page_home
from .navigation import construire_pages

# --- DIAGNOSTIC TEMPORAIRE (à retirer) -----------------------------------
# Streamlit Cloud masque le message des ImportError. On importe ici, en
# capturant la trace complète pour l'afficher dans l'application.
_ERREUR_IMPORT = None
try:
    from .accueil import rendre as rendre_accueil
    from .ui import selecteur_session_global
except BaseException:
    import traceback

    _ERREUR_IMPORT = traceback.format_exc()

    def rendre_accueil() -> None:
        st.error("DIAGNOSTIC — import de .accueil / .ui impossible :")
        st.code(_ERREUR_IMPORT)

        # Que contient réellement le src/ui.py déployé ?
        from pathlib import Path as _P

        import src.ui as _u

        chemin = _P(_u.__file__)
        source = chemin.read_text(encoding="utf-8")
        st.write(f"**src/ui.py déployé** : {len(source)} octets, "
                 f"{len(source.splitlines())} lignes")
        st.write("**attributs publics** :",
                 sorted(a for a in dir(_u) if not a.startswith("_")))
        st.write("**'barre_contexte' dans la source** :",
                 "barre_contexte" in source)
        st.code("\n".join(
            f"{i}: {l}" for i, l in enumerate(source.splitlines(), 1)
            if l.startswith("def ") or l.startswith("SESSIONS")
            or l.startswith("AUTO_CHARGEMENT")))

    def selecteur_session_global() -> None:
        pass
# --- fin du diagnostic ---------------------------------------------------


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
