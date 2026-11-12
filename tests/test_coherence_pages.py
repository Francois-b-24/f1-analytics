"""Cohérence de présentation entre les pages — analyse statique, hors ligne.

Avant cette phase, chaque page avait sa propre convention : `st.subheader`
partout pour le titre, sauf la page Classements qui n'en avait aucun ; une
seule page utilisait `help=` ; les tableaux de classement étaient rendus en
HTML brut. Ces tests empêchent le retour de ces divergences.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.navigation import entrees_declarees

RACINE = Path(__file__).resolve().parent.parent

# L'accueil porte un titre en HTML stylé (identité visuelle : dégradé, emoji),
# volontairement différent du `st.title` des autres pages.
_SANS_TITRE_STANDARD = {"pages/accueil.py"}


def _source(fichier: str) -> str:
    return (RACINE / fichier).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "fichier",
    [e["fichier"] for e in entrees_declarees() if e["fichier"] not in _SANS_TITRE_STANDARD],
)
def test_chaque_page_a_un_entete_standard(fichier):
    """Un seul appel, en tête : titre, accroche et aide à la lecture."""
    source = _source(fichier)

    assert source.count("entete_page(") == 1, (
        f"{fichier} doit appeler entete_page() exactement une fois"
    )


@pytest.mark.parametrize("fichier", [e["fichier"] for e in entrees_declarees()])
def test_aucune_page_nutilise_subheader_comme_titre(fichier):
    """`st.subheader` reste pour les sections internes, jamais pour le titre.

    On vérifie qu'aucun subheader ne précède l'en-tête de page.
    """
    source = _source(fichier)
    if "entete_page(" not in source:
        return  # accueil : titre HTML stylé, traité à part

    avant_entete = source[: source.index("entete_page(")]
    assert "st.subheader(" not in avant_entete, (
        f"{fichier} place un st.subheader avant son titre de page"
    )


@pytest.mark.parametrize("fichier", [e["fichier"] for e in entrees_declarees()])
def test_aucun_tableau_en_html_brut(fichier):
    """`to_html` + `unsafe_allow_html` prive du tri, du redimensionnement et du CSS."""
    source = _source(fichier)

    assert "to_html(" not in source, (
        f"{fichier} rend un tableau en HTML brut : utiliser st.dataframe()"
    )


@pytest.mark.parametrize("fichier", [e["fichier"] for e in entrees_declarees()])
def test_pas_de_parametre_deprecie(fichier):
    """`use_container_width` est déprécié depuis fin 2025 au profit de `width`."""
    source = _source(fichier)

    assert "use_container_width" not in source, (
        f"{fichier} utilise use_container_width : remplacer par width=\"stretch\""
    )


def test_la_garde_de_session_precede_tout_rendu_de_classements():
    """Régression : les onglets étaient créés avant la garde.

    Des onglets vides s'affichaient alors au-dessus du message expliquant
    qu'aucune session n'était chargée.
    """
    source = _source("pages/classements.py")

    assert source.index("selections_courantes") < source.index("st.tabs"), (
        "la garde de session doit précéder la création des onglets"
    )


def test_le_css_ne_reference_pas_de_police_non_chargee():
    """Une police nommée sans @import ni @font-face est un repli silencieux."""
    css = (RACINE / "f1_theme.css").read_text(encoding="utf-8")
    declarations = [
        ligne for ligne in css.splitlines()
        if "font-family" in ligne and not ligne.strip().startswith(("/*", "*"))
    ]

    for ligne in declarations:
        if "Inter" in ligne:
            assert "@import" in css or "@font-face" in css, (
                "'Inter' est référencée sans être chargée : "
                "soit l'importer, soit assumer la pile système"
            )


def test_le_css_nintroduit_pas_de_couleur_en_dur_dans_les_classes_custom():
    """CLAUDE.md : src/theme.py est la source de vérité des couleurs."""
    css = (RACINE / "f1_theme.css").read_text(encoding="utf-8")
    bloc = css[css.index(".f1-carte {"):]

    import re
    # On ignore les commentaires, qui peuvent citer une valeur à titre d'exemple.
    sans_commentaires = re.sub(r"/\*.*?\*/", "", bloc, flags=re.S)
    hex_en_dur = re.findall(r"#[0-9a-fA-F]{3,6}", sans_commentaires)

    assert not hex_en_dur, (
        f"couleurs en dur dans les classes custom : {hex_en_dur} — utiliser var(--…)"
    )
