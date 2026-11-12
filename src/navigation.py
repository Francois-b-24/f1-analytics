"""Registre des pages et construction de la navigation.

Remplace la découverte automatique du dossier `pages/`, qui dérivait les
libellés des noms de fichiers : la barre latérale affichait « 1 Chronos &
Télémetries » ou « 10 Energie & 2026 », numéros, underscores et fautes
d'accent compris, dans un ordre lexicographique plaçant la page 10 juste après
la page 1.

Deux précautions :

- `url_path` est **épinglé** sur chaque page. Sans lui, `st.Page` dérive l'URL
  du nom de fichier, et le renommage des fichiers casserait les liens et
  favoris existants.
- Les objets `st.Page` sont reconstruits à chaque run (pas de cache) : une page
  porte un drapeau à usage unique consommé par `run()`.
"""
from __future__ import annotations

import streamlit as st

# Un seul endroit décrit chaque page : fichier, libellé, icône, URL.
# L'ordre des sections et des entrées est celui de la barre latérale.
_STRUCTURE: dict[str, list[dict[str, str]]] = {
    "Vue d'ensemble": [
        {"fichier": "pages/accueil.py", "titre": "Accueil",
         "icone": ":material/home:", "url": "accueil", "defaut": True},
        {"fichier": "pages/classements.py", "titre": "Classements",
         "icone": ":material/emoji_events:", "url": "classements"},
    ],
    "Performance": [
        {"fichier": "pages/chronos_telemetries.py", "titre": "Chronos & télémétries",
         "icone": ":material/timer:", "url": "chronos"},
        {"fichier": "pages/secteurs.py", "titre": "Analyse par secteur",
         "icone": ":material/straighten:", "url": "secteurs"},
        {"fichier": "pages/positions.py", "titre": "Positions par tour",
         "icone": ":material/trending_up:", "url": "positions"},
    ],
    "Course & stratégie": [
        {"fichier": "pages/pneus_strategies.py", "titre": "Pneus & stratégies",
         "icone": ":material/tire_repair:", "url": "pneus"},
        {"fichier": "pages/arrets.py", "titre": "Arrêts aux stands",
         "icone": ":material/build:", "url": "arrets"},
        {"fichier": "pages/meteo.py", "titre": "Météo",
         "icone": ":material/thermostat:", "url": "meteo"},
    ],
    "Avancé & données": [
        {"fichier": "pages/cartographie.py", "titre": "Cartographie du circuit",
         "icone": ":material/map:", "url": "cartographie"},
        {"fichier": "pages/energie_2026.py", "titre": "Énergie & 2026",
         "icone": ":material/bolt:", "url": "energie-2026"},
        {"fichier": "pages/exports.py", "titre": "Exports de données",
         "icone": ":material/download:", "url": "exports"},
    ],
    "À propos": [
        {"fichier": "pages/glossaire.py", "titre": "Glossaire & méthodologie",
         "icone": ":material/menu_book:", "url": "glossaire"},
    ],
}

# Pages référencées ailleurs par un lien : on expose un constructeur plutôt
# qu'un chemin en dur, pour qu'un renommage ne casse pas le lien.
_FICHIER_ACCUEIL = "pages/accueil.py"
_FICHIER_GLOSSAIRE = "pages/glossaire.py"


def construire_sections() -> dict[str, list]:
    """Construit le dict {section: [st.Page, ...]} attendu par `st.navigation`."""
    return {
        section: [
            st.Page(
                entree["fichier"],
                title=entree["titre"],
                icon=entree["icone"],
                url_path=entree["url"],
                default=bool(entree.get("defaut")),
            )
            for entree in entrees
        ]
        for section, entrees in _STRUCTURE.items()
    }


def page_accueil():
    """Objet `st.Page` de l'accueil, pour `st.page_link` depuis une autre page.

    `st.page_link` accepte un `StreamlitPage` : passer l'objet plutôt qu'un
    chemin en dur évite qu'un renommage de fichier ne casse silencieusement
    les liens de retour.
    """
    return st.Page(
        _FICHIER_ACCUEIL,
        title="Accueil",
        icon=":material/home:",
        url_path="accueil",
        default=True,
    )


def entrees_declarees() -> list[dict[str, str]]:
    """Toutes les entrées, à plat — utilisé par les tests de cohérence."""
    return [entree for entrees in _STRUCTURE.values() for entree in entrees]


def page_glossaire():
    """Objet `st.Page` du glossaire, pour le lien depuis la barre latérale."""
    return st.Page(
        _FICHIER_GLOSSAIRE,
        title="Glossaire & méthodologie",
        icon=":material/menu_book:",
        url_path="glossaire",
    )
