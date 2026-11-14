"""Point d'entrée de l'application.

Pourquoi ce fichier, et pourquoi il déclare la navigation
---------------------------------------------------------
La production n'affichait plus aucune page : barre latérale absente, dix
onglets inatteignables, et pas la moindre erreur dans les logs — l'app servait
l'accueil seul. Le serveur Streamlit Cloud n'annonçait qu'une page dans son
message de session, alors que le même code annonçait les dix en local.

Cause : la navigation reposait sur la découverte implicite du dossier
``pages/``, que Streamlit n'active que si ce dossier est adjacent au fichier
d'entrée, test effectué une seule fois au démarrage du process. Le « Main file
path » configuré côté Cloud vit hors du dépôt : aucun test ne pouvait l'attraper
et rien dans le code ne permettait de le corriger.

``src/navigation.py`` déclare donc les pages explicitement, ancrées sur la
racine du projet. L'app expose les mêmes dix pages quel que soit le fichier
d'entrée lancé et quel que soit le répertoire courant.

Les deux points d'entrée restent équivalents :

    streamlit run Home.py
    streamlit run streamlit_app.py
"""
import runpy
from pathlib import Path

import streamlit as st

from src.config import configure_page_home
from src.navigation import construire_pages
from src.ui import selecteur_session_global

configure_page_home("F1 Analytics")

_HOME = Path(__file__).resolve().parent / "Home.py"


def _accueil() -> None:
    """Rend la page d'accueil.

    ``Home.py`` est exécuté comme un script plutôt qu'importé : il s'exécute
    de haut en bas et n'expose aucune fonction de rendu. ``run_name`` n'est
    pas ``"__main__"`` ici — l'accueil est une page parmi d'autres, et
    ``set_page_config()`` a déjà été appelé ci-dessus.
    """
    runpy.run_path(str(_HOME), run_name="__page__")


pages = st.navigation(construire_pages(_accueil))

# Rendu ici, et nulle part ailleurs : la barre latérale appartient au routeur,
# donc le sélecteur existe sur toutes les pages et ses clés ne peuvent pas
# être rendues deux fois dans un même run (`StreamlitDuplicateElementKey`).
# Avant `.run()` pour que la page lise une sélection déjà à jour.
selecteur_session_global()

pages.run()
