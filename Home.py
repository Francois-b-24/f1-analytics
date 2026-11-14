"""Point d'entrée historique de l'application.

Streamlit Cloud peut être configuré sur `Home.py` comme sur
`streamlit_app.py` : le « Main file path » vit chez l'hébergeur, hors du
dépôt, et c'est la cause racine d'une panne passée où la production ne servait
plus aucune page. Les deux fichiers doivent donc rester des points d'entrée
valides et équivalents.

Ce fichier ne contient plus que la délégation. Le rendu de l'accueil vit dans
`src/accueil.py` : tant qu'il était ici, ce fichier cumulait deux rôles —
point d'entrée et page — et se relançait lui-même par `runpy` au milieu de ses
propres imports, ce qui cassait l'accueil en production.
"""
import runpy
import sys
import traceback
from pathlib import Path

import streamlit as st

# --- DIAGNOSTIC TEMPORAIRE (à retirer) -----------------------------------
# Streamlit Cloud masque le message des ImportError. On importe src.ui ici,
# avant toute autre chose, et on affiche la trace complète à l'écran.
_RACINE = str(Path(__file__).resolve().parent)
if _RACINE not in sys.path:
    sys.path.insert(0, _RACINE)
try:
    import src.ui  # noqa: F401
except BaseException:
    st.error("DIAGNOSTIC — import de src.ui impossible :")
    st.code(traceback.format_exc())
    st.caption(f"python={sys.version} | sys.path[0:3]={sys.path[0:3]}")
    st.stop()
# --- fin du diagnostic ---------------------------------------------------

runpy.run_path(
    str(Path(__file__).resolve().parent / "streamlit_app.py"),
    run_name="__main__",
)
