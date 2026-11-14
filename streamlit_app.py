"""Point d'entrée de l'application.

Équivalent à `Home.py` : le « Main file path » est configuré chez
l'hébergeur, hors du dépôt, donc les deux doivent fonctionner. Le montage vit
dans `src/routeur.py`, importé comme un module ordinaire — `runpy` créait un
second contexte d'import qui cassait la production.

    streamlit run Home.py
    streamlit run streamlit_app.py
"""
import src.routeur

src.routeur.demarrer()
