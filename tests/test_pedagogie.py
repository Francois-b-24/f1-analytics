"""Cohérence du contenu pédagogique — hors ligne.

Transforme l'intention « chaque page s'explique » en invariant vérifié : sans
ces tests, une page ajoutée sans texte passerait inaperçue jusqu'à ce qu'un
lecteur tombe sur un en-tête muet.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.navigation import entrees_declarees
from src.pedagogie import EXPLICATIONS, GLOSSAIRE, aide, explication

RACINE = Path(__file__).resolve().parent.parent


def _cles_de_page() -> set[str]:
    """Nom de module de chaque page déclarée, sans le dossier ni .py."""
    return {Path(e["fichier"]).stem for e in entrees_declarees()}


def test_chaque_page_a_son_texte():
    manquantes = sorted(_cles_de_page() - set(EXPLICATIONS))

    assert not manquantes, f"pages sans texte pédagogique : {manquantes}"


def test_aucun_texte_orphelin():
    """Un texte sans page correspondante est du contenu mort."""
    orphelins = sorted(set(EXPLICATIONS) - _cles_de_page())

    assert not orphelins, f"textes sans page : {orphelins}"


@pytest.mark.parametrize("cle", sorted(EXPLICATIONS))
def test_chaque_texte_est_exploitable(cle):
    textes = EXPLICATIONS[cle]

    assert textes["titre"], f"{cle} : titre vide"
    assert not textes["titre"].endswith("."), f"{cle} : un titre n'est pas une phrase"
    # Le glossaire n'a pas d'accroche de lecture, c'est lui-même l'explication.
    if cle != "glossaire":
        assert len(textes["accroche"]) > 40, f"{cle} : accroche trop courte pour informer"
        assert len(textes["lecture"]) > 40, f"{cle} : aide à la lecture trop courte"


def test_explication_a_un_repli_pour_page_inconnue():
    """Une page pas encore documentée ne doit pas faire échouer le rendu."""
    repli = explication("page_inexistante")

    assert repli["titre"]
    assert repli["accroche"] == ""


@pytest.mark.parametrize("terme", sorted(GLOSSAIRE))
def test_chaque_definition_est_courte_et_utile(terme):
    definition = GLOSSAIRE[terme]

    assert 20 < len(definition) < 320, f"{terme} : définition de {len(definition)} caractères"
    assert definition[0].isupper(), f"{terme} : définition sans majuscule initiale"
    assert definition.rstrip().endswith("."), f"{terme} : définition sans point final"


def test_aide_retourne_vide_sur_terme_inconnu():
    """Une coquille ne doit pas afficher d'infobulle trompeuse."""
    assert aide("terme qui n'existe pas") == ""
    assert aide("Delta")


def test_les_termes_du_raccourci_existent():
    """Le raccourci de la barre latérale ne doit pas citer un terme absent.

    Sinon `GLOSSAIRE[terme]` lèverait un KeyError au rendu de **chaque** page,
    puisque le raccourci est dans la barre latérale du routeur.
    """
    from src.ui import TERMES_RACCOURCI

    assert TERMES_RACCOURCI, "le raccourci doit citer quelques termes"
    inconnus = [t for t in TERMES_RACCOURCI if t not in GLOSSAIRE]
    assert not inconnus, f"termes cités mais absents du glossaire : {inconnus}"
