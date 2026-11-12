"""Alias du point d'entrée — délègue à Home.py.

Raison d'être : le réglage « Main file path » de Streamlit Cloud vit dans les
paramètres de l'app, hors du dépôt. Il pointe sur `streamlit_app.py`, nom hérité
de la phase 2 et supprimé depuis. Résultat en production : Streamlit démarrait
sans erreur mais ne découvrait pas le dossier `pages/`, car la découverte
implicite exige que `pages/` soit adjacent au fichier d'entrée. L'app servait
donc l'accueil seul, barre latérale vide, les dix onglets inatteignables.

Ce fichier rétablit ce nom à la racine, à côté de `pages/`. Les deux points
d'entrée sont désormais équivalents :

    streamlit run Home.py
    streamlit run streamlit_app.py

Volontairement mince : il ne réintroduit ni `src/navigation.py` ni le routeur
`st.navigation` de la phase 2, tous deux retirés. La navigation reste implicite,
fondée sur le dossier `pages/`.

`runpy` exécute Home.py sous le nom `__main__`, donc exactement comme le ferait
un lancement direct : `st.set_page_config()` y reste le premier appel Streamlit.
Un simple `import` aurait fait porter le nom de module `Home` au script, ce qui
n'est pas la façon dont Streamlit attend qu'un point d'entrée soit exécuté.
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).parent / "Home.py"), run_name="__main__")
