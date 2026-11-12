"""Garde-fou sur les points d'entrée de l'application.

Contexte : la production a servi pendant un temps l'accueil seul, barre latérale
vide et dix onglets inatteignables. Le code était pourtant sain — lint, tests et
CI tous verts. La cause était le réglage « Main file path » de Streamlit Cloud,
qui pointait sur `streamlit_app.py`, fichier supprimé du dépôt entre-temps.

Streamlit démarre sans erreur dans ce cas : la découverte des pages est
implicite et exige seulement que `pages/` soit adjacent au fichier d'entrée.
Quand ce n'est pas le cas, l'app tourne, mais sans aucune page.

Ces tests vérifient donc ce qu'aucun test ne couvrait : que tout point d'entrée
supporté existe à la racine, à côté de `pages/`, et que les dix pages restent
découvrables. Ils sont hors ligne — aucun appel réseau.
"""
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
POINTS_ENTREE = ("Home.py", "streamlit_app.py")
NB_PAGES_ATTENDU = 10


@pytest.mark.parametrize("nom", POINTS_ENTREE)
def test_point_entree_existe_a_la_racine(nom):
    """Chaque point d'entrée supporté est présent à la racine du dépôt."""
    chemin = RACINE / nom
    assert chemin.is_file(), (
        f"{nom} est absent de la racine. Streamlit Cloud peut être configuré "
        f"pour le lancer : son absence laisse l'app démarrer sans aucune page."
    )


@pytest.mark.parametrize("nom", POINTS_ENTREE)
def test_pages_adjacentes_au_point_entree(nom):
    """`pages/` est adjacent au point d'entrée — condition de la découverte."""
    dossier = (RACINE / nom).parent / "pages"
    assert dossier.is_dir(), (
        f"pages/ n'est pas à côté de {nom} : la navigation implicite de "
        f"Streamlit ne trouverait aucune page."
    )


def test_les_dix_pages_sont_presentes():
    """Les dix onglets attendus sont découvrables."""
    pages = sorted(p.name for p in (RACINE / "pages").glob("*.py"))
    assert len(pages) == NB_PAGES_ATTENDU, f"Pages trouvées : {pages}"


def test_alias_delegue_bien_a_home():
    """L'alias exécute Home.py sans réintroduire le routeur retiré.

    Lecture statique : exécuter le fichier lancerait Streamlit hors contexte.
    """
    source = (RACINE / "streamlit_app.py").read_text(encoding="utf-8")
    assert "Home.py" in source, "L'alias ne référence pas Home.py."
    assert "run_name=\"__main__\"" in source, (
        "Home.py doit être exécuté sous __main__, sinon st.set_page_config() "
        "n'est plus le premier appel Streamlit."
    )
    assert "src.navigation" not in source, (
        "src/navigation.py a été retiré du projet : l'alias ne doit pas le "
        "réintroduire."
    )
