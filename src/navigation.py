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
    ("1_Chronos_&_Télémetries.py", "Chronos & télémétries", "⏱️"),
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


# Regroupement thématique de la barre latérale.
#
# Dix onglets à plat se lisaient mal. Les sections suivent le déroulé d'un
# week-end : ce qui s'est passé, qui était rapide, comment la course s'est
# jouée, puis l'exploration technique.
#
# C'est une vue d'affichage, pas un registre : `_DECLARATION` reste la source
# de vérité et ses tests restent inchangés. Les fichiers ne sont ni renommés
# ni déplacés — c'est un renommage de pages qui avait cassé la production.
_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Le week-end", (
        "5_Classements.py",
        "4_Meteo.py",
    )),
    ("Performance", (
        "1_Chronos_&_Télémetries.py",
        "2_Performances.py",
        "9_Secteurs.py",
    )),
    ("Stratégie", (
        "3_Pneus_&_strategies.py",
        "6_Pitstops.py",
    )),
    ("Technique & données", (
        "7_Cartographie.py",
        "10_Energie_&_2026.py",
        "8_Exports_de_donnees.py",
    )),
)


# Page d'accueil courante, mémorisée au moment où la navigation est montée.
# `st.page_link` exige un StreamlitPage sous `st.navigation` : un chemin de
# fichier n'y est plus résolvable et lève StreamlitPageNotFoundError.
_ACCUEIL: st.navigation | None = None


def construire_pages(accueil) -> dict[str, list[st.navigation]]:
    """Construit les pages groupées par section, accueil en tête.

    ``accueil`` est le callable rendant la page d'accueil. Les fichiers
    absents sont ignorés silencieusement plutôt que de casser toute la
    navigation : une page manquante ne doit pas rendre l'app inutilisable.

    Retourne un dict section → pages, accepté par ``st.navigation``. La page
    par défaut est cherchée dans toutes les sections, donc l'accueil reste
    celle qui s'ouvre. Les sections vides sont écartées : elles afficheraient
    un titre sans contenu.

    Une page déclarée dans ``_DECLARATION`` mais absente de ``_SECTIONS``
    serait injoignable ; elle est rattachée à la dernière section plutôt que
    perdue, et ``tests/test_points_entree.py`` interdit ce cas de figure.
    """
    global _ACCUEIL

    _ACCUEIL = st.Page(accueil, title="Home", icon="🏎️", default=True)
    titres = {fichier: (titre, icone) for fichier, titre, icone in _DECLARATION}

    def _page(fichier: str):
        chemin = _PAGES / fichier
        if not chemin.is_file() or fichier not in titres:
            return None
        titre, icone = titres[fichier]
        return st.Page(chemin, title=titre, icon=icone)

    groupes: dict[str, list[st.navigation]] = {}
    classes: set[str] = set()
    for section, fichiers in _SECTIONS:
        pages = [p for p in (_page(f) for f in fichiers) if p is not None]
        classes.update(fichiers)
        if pages:
            groupes[section] = pages

    # Filet : aucune page déclarée ne doit rester hors navigation.
    oubliees = [p for p in (_page(f) for f, _, _ in _DECLARATION
                            if f not in classes) if p is not None]
    if oubliees and groupes:
        groupes[list(groupes)[-1]].extend(oubliees)
    elif oubliees:
        groupes["Pages"] = oubliees

    # L'accueil ouvre la première section plutôt qu'une section à lui seul.
    premiere = next(iter(groupes), "Le week-end")
    ordonnees = {premiere: [_ACCUEIL, *groupes.get(premiere, [])]}
    ordonnees.update({k: v for k, v in groupes.items() if k != premiere})
    return ordonnees


def lien_accueil(label: str = "🏠 Aller à la page Home") -> None:
    """Affiche un lien vers l'accueil, quel que soit le mode de navigation.

    Sous ``st.navigation``, les pages sont identifiées par leur objet
    ``StreamlitPage`` et non par leur chemin : ``st.page_link("Home.py")``
    y lève ``StreamlitPageNotFoundError``. Cette fonction utilise l'objet
    mémorisé, et retombe sur le chemin de fichier quand la navigation
    implicite est active (aucune page déclarée).

    Le lien est décoratif : son échec ne doit jamais interrompre la page qui
    l'affiche, d'où le repli silencieux.
    """
    try:
        if _ACCUEIL is not None:
            st.page_link(_ACCUEIL, label=label)
        else:
            st.page_link(str(_RACINE / "Home.py"), label=label)
    except Exception:  # noqa: BLE001 — un lien cassé ne doit pas casser la page
        pass
