"""Déclaration explicite des pages de l'application.

Pourquoi ce module existe
-------------------------
La navigation reposait jusqu'ici sur la découverte implicite du dossier
``pages/``. Streamlit ne l'active que si ce dossier est adjacent au fichier
d'entrée, test fait une seule fois au démarrage du process :

    uses_pages_directory = Path(main_script_parent / "pages").exists()

En production, ce test renvoyait False : le serveur n'annonçait que ``Home.py``
dans son message de session, la barre latérale était absente et les dix onglets
inatteignables — sans la moindre erreur dans les logs, l'app se contentant de
servir l'accueil.

La déclaration explicite ci-dessous retire cette dépendance au chemin : les
pages sont ancrées sur ``__file__`` (donc sur la racine du projet) et non sur
le répertoire du script lancé ni sur le répertoire courant. L'application
expose ainsi les mêmes dix pages quel que soit le fichier d'entrée configuré.

Les chemins sont absolus de façon délibérée : ``st.Page`` résout les chemins
relatifs depuis le fichier d'entrée, pas depuis le module qui les déclare — un
point d'entrée situé ailleurs lèverait « Unable to create Page ».
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

_RACINE = Path(__file__).resolve().parent.parent
_PAGES = _RACINE / "pages"

# (fichier, libellé, icône). L'ordre fixe celui de la barre latérale et
# reprend la numérotation historique des fichiers.
_DECLARATION: tuple[tuple[str, str, str], ...] = (
    ("1_Chronos_&_Télémetries.py", "Chronos & Télémetries", "⏱️"),
    ("2_Performances.py", "Performances", "📈"),
    ("3_Pneus_&_strategies.py", "Pneus & stratégies", "🛞"),
    ("4_Meteo.py", "Météo", "🌦️"),
    ("5_Classements.py", "Classements", "🏆"),
    ("6_Pitstops.py", "Arrêts aux stands", "🔧"),
    ("7_Cartographie.py", "Cartographie", "🗺️"),
    ("8_Exports_de_donnees.py", "Exports de données", "📤"),
    ("9_Secteurs.py", "Secteurs", "📐"),
    ("10_Energie_&_2026.py", "Énergie & 2026", "⚡"),
)


def construire_pages(accueil) -> list[st.navigation]:
    """Construit la liste des pages, accueil en tête.

    ``accueil`` est le callable rendant la page d'accueil. Les fichiers
    absents sont ignorés silencieusement plutôt que de casser toute la
    navigation : une page manquante ne doit pas rendre l'app inutilisable.
    """
    pages = [st.Page(accueil, title="Home", icon="🏎️", default=True)]
    for fichier, titre, icone in _DECLARATION:
        chemin = _PAGES / fichier
        if chemin.is_file():
            pages.append(st.Page(chemin, title=titre, icon=icone))
    return pages
