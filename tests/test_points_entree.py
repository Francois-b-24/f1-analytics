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


def test_navigation_explicite_declaree():
    """Le routeur déclare les pages explicitement, pas par découverte implicite.

    C'est ce qui a cassé la production : la découverte implicite n'est active
    que si `pages/` est adjacent au fichier d'entrée, condition invérifiable
    depuis le dépôt puisque le chemin d'entrée est configuré chez l'hébergeur.
    """
    source = (RACINE / "streamlit_app.py").read_text(encoding="utf-8")
    assert "st.navigation" in source, (
        "Le routeur doit déclarer les pages via st.navigation, sinon la "
        "navigation redevient dépendante du chemin du fichier d'entrée."
    )
    assert "construire_pages" in source


def test_home_delegue_au_routeur_si_lance_directement():
    """Lancé directement, Home.py délègue au routeur.

    Sans cela, un hébergeur configuré sur Home.py rendrait l'accueil seul,
    sans barre latérale — le symptôme exact observé en production.
    """
    source = (RACINE / "Home.py").read_text(encoding="utf-8")
    assert '__name__ == "__main__"' in source
    assert "streamlit_app.py" in source


def test_navigation_ancre_les_chemins_sur_la_racine():
    """Les pages sont ancrées sur __file__, pas sur le répertoire courant.

    st.Page résout les chemins relatifs depuis le fichier d'entrée : un
    ancrage relatif casserait dès que l'entrée n'est pas à la racine.
    """
    source = (RACINE / "src" / "navigation.py").read_text(encoding="utf-8")
    assert "__file__" in source


def test_toutes_les_pages_sont_declarees():
    """Chaque fichier de pages/ figure dans la déclaration du routeur."""
    from src.navigation import _DECLARATION

    declares = {nom for nom, _, _ in _DECLARATION}
    sur_disque = {p.name for p in (RACINE / "pages").glob("*.py")}
    manquants = sur_disque - declares
    assert not manquants, f"Pages non déclarées dans le routeur : {manquants}"


def test_aucun_page_link_par_chemin():
    """Aucun `st.page_link("Home.py")` ne subsiste dans l'app.

    Sous `st.navigation`, les pages sont identifiées par leur objet
    `StreamlitPage` : un chemin de fichier y lève
    `StreamlitPageNotFoundError`. C'est ce qui cassait les dix onglets en
    production dès qu'une page affichait son lien de retour à l'accueil.
    `src/navigation.py` est exclu : il porte le repli documenté.
    """
    fautifs = []
    for chemin in [RACINE / "Home.py", *(RACINE / "pages").glob("*.py"),
                   *(RACINE / "src").glob("*.py")]:
        if chemin.name == "navigation.py":
            continue
        if 'page_link("Home.py"' in chemin.read_text(encoding="utf-8"):
            fautifs.append(chemin.name)
    assert not fautifs, (
        f"st.page_link par chemin dans : {fautifs}. Utiliser lien_accueil()."
    )
