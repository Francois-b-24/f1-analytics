"""Point d'entrée historique — délègue au routeur `streamlit_app.py`.

Pourquoi ce fichier existe : l'application déployée sur Streamlit Cloud est
configurée pour lancer `Home.py`, et ce réglage vit dans les paramètres de
l'app, hors du dépôt. Le renommage du point d'entrée en `streamlit_app.py` a
donc cassé le démarrage en production (« Error running app ») alors que tout
passait en local et en CI.

Ce fichier rétablit le démarrage sans intervention manuelle. Les deux points
d'entrée sont équivalents : `src/navigation.py` résout les pages depuis la
racine du projet, pas depuis le script lancé.

Pour le retirer : changer « Main file path » en `streamlit_app.py` dans les
réglages de l'app (Manage app → Settings), vérifier que l'app démarre, puis
supprimer ce fichier.
"""

import streamlit_app  # noqa: F401  (l'import exécute le routeur)
