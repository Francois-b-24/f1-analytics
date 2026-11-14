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
import streamlit as st

import traceback as _tb

from src.config import configure_page_home
from src.accueil import rendre as rendre_accueil
from src.navigation import construire_pages
from src.ui import selecteur_session_global

configure_page_home("F1 Analytics")

# --- DIAGNOSTIC TEMPORAIRE (à retirer) -----------------------------------
# La production lève ImportError sur `from .ui import ...` sans jamais
# divulguer le message. On le capture et on l'affiche.
try:
    import src.ui as _diag_ui
    st.success(f"src.ui importé — attributs : {len([a for a in dir(_diag_ui) if not a.startswith('_')])}")
except BaseException:
    st.error("DIAGNOSTIC — échec d'import de src.ui :")
    st.code(_tb.format_exc())
    st.stop()
# --- fin du diagnostic ---------------------------------------------------

pages = st.navigation(construire_pages(rendre_accueil))

# Rendu ici, et nulle part ailleurs : la barre latérale appartient au routeur,
# donc le sélecteur existe sur toutes les pages et ses clés ne peuvent pas
# être rendues deux fois dans un même run (`StreamlitDuplicateElementKey`).
# Avant `.run()` pour que la page lise une sélection déjà à jour.
selecteur_session_global()

pages.run()
