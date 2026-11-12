"""Cohérence du registre de navigation — hors ligne.

Ces tests attrapent le mode d'échec propre à cette phase : un fichier renommé
sans que le registre suive. `st.Page` vérifie l'existence du fichier à la
construction, mais seulement à l'exécution de l'app — ici on le vérifie en CI.
"""
from __future__ import annotations

from pathlib import Path

from src.navigation import entrees_declarees

RACINE = Path(__file__).resolve().parent.parent


def test_chaque_page_declaree_existe_sur_disque():
    manquants = [e["fichier"] for e in entrees_declarees()
                 if not (RACINE / e["fichier"]).is_file()]

    assert not manquants, f"déclarées mais absentes : {manquants}"


def test_chaque_page_du_dossier_est_declaree():
    """L'inverse : une page ajoutée sans être déclarée serait inaccessible."""
    sur_disque = {f"pages/{p.name}" for p in (RACINE / "pages").glob("*.py")}
    declarees = {e["fichier"] for e in entrees_declarees()}

    assert sur_disque == declarees, (
        f"non déclarées : {sorted(sur_disque - declarees)} ; "
        f"déclarées en trop : {sorted(declarees - sur_disque)}"
    )


def test_une_seule_page_par_defaut():
    defauts = [e["titre"] for e in entrees_declarees() if e.get("defaut")]

    assert len(defauts) == 1, f"il faut exactement une page par défaut, trouvé {defauts}"


def test_les_url_sont_uniques_et_stables():
    """`url_path` est épinglé pour que renommer un fichier ne casse pas les liens."""
    urls = [e["url"] for e in entrees_declarees()]

    assert len(urls) == len(set(urls)), "deux pages partagent la même URL"
    assert all(u and " " not in u for u in urls), f"URL mal formée dans {urls}"


def test_les_libelles_sont_propres():
    """Plus de numéros de fichier ni d'underscores dans ce que voit l'utilisateur."""
    for entree in entrees_declarees():
        titre = entree["titre"]
        assert "_" not in titre, f"underscore dans le libellé : {titre!r}"
        assert not titre[0].isdigit(), f"libellé commençant par un chiffre : {titre!r}"


def test_aucune_page_ne_configure_la_page_elle_meme():
    """Garde-fou contre une régression silencieuse.

    `set_page_config` est appelable plusieurs fois, et le dernier appel gagne :
    une page qui le rappellerait écraserait sans erreur le titre d'onglet et le
    menu « About » posés par le routeur. Aucun avertissement ne le signalerait.
    """
    fautives = []
    for entree in entrees_declarees():
        source = (RACINE / entree["fichier"]).read_text(encoding="utf-8")
        if "set_page_config" in source or "configure_page" in source:
            fautives.append(entree["fichier"])

    assert not fautives, (
        f"ces pages configurent la page alors que c'est le rôle du routeur : {fautives}"
    )


def test_le_routeur_est_le_seul_a_configurer_la_page():
    source = (RACINE / "streamlit_app.py").read_text(encoding="utf-8")

    assert "configure_page_home" in source
    assert "st.navigation" in source
