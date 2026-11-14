"""Point d'entrée historique de l'application.

Streamlit Cloud peut être configuré sur `Home.py` comme sur
`streamlit_app.py` : le « Main file path » vit chez l'hébergeur, hors du
dépôt, et c'est la cause racine d'une panne passée où la production ne servait
plus aucune page. Les deux fichiers doivent donc rester des points d'entrée
valides et équivalents.

Pourquoi un import et non `runpy`
---------------------------------
Ce fichier déléguait au routeur par `runpy.run_path`, qui exécute un fichier
dans un module neuf baptisé `__main__`. Les modules du paquet `src` importés
par ce second exécutable sont alors **réimportés dans un autre contexte**, et
la production levait `ImportError` sur `from .ui import …` — jamais reproduit
en local, où l'ordre d'import diffère. Un diagnostic déployé en production a
tranché : `import src.ui` placé avant la délégation réussissait, et l'échec
survenait dans la réimportation faite par `runpy`.

Le routeur est donc importé comme un module ordinaire. Il n'y a plus qu'une
seule importation de chaque module, dans un seul contexte.
"""
import src.routeur

src.routeur.demarrer()
