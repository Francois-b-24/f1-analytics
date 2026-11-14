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
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "streamlit_app.py"),
    run_name="__main__",
)
