import streamlit as st

from src.data import (
    agreger_classement_constructeurs,
    agreger_classement_pilotes,
    calcul_classement_constructeur,
    calcul_classement_pilote,
    classement_session,
    ergast_couvre,
    manches_de_la_saison,
    points_par_course_progressif,
)
from src.session import charger_session_ou_stopper
from src.ui import entete_page, selections_courantes

entete_page("classements")

annee, grand_prix, session_type, loaded = selections_courantes(required=True)

data = charger_session_ou_stopper(annee, grand_prix, session_type)
tours = data["tours"]
resultats = data["resultats"]

# Onglets créés après la garde : sinon ils s'affichent, vides, au-dessus du
# message expliquant qu'aucune session n'est chargée.
t1, t2 = st.tabs(["Classement session", "Championnat"])

with t1:
    st.subheader(f"Classement – {session_type}")
    cls = classement_session(tours, resultats, session_type)
    if not cls.empty:
        st.dataframe(cls, hide_index=True, width="stretch")
    else:
        st.info("Classement indisponible pour cette session.")


def _championnat_progressif(annee: int, grand_prix: str) -> None:
    """Cumule les points lot par lot, en affichant un résultat utilisable.

    Pourquoi ce détour plutôt qu'un simple appel : un classement cumulé exige
    de parcourir toute la saison, et le quota OpenF1 impose des attentes
    pouvant atteindre 20 s par requête. L'ancien chargement en un bloc prenait
    39 s puis 123 s sur la saison 2026 — au-delà du délai toléré par
    l'hébergement, ce qui faisait tomber l'application.

    Un cumul partiel reste **exact** (c'est une somme de points), simplement
    incomplet : on peut donc l'afficher au fur et à mesure, en annonçant le
    nombre de manches prises en compte.
    """
    manches = manches_de_la_saison(annee, grand_prix)
    if manches is None:
        st.info(
            "Impossible de situer ce Grand Prix dans la saison — "
            "classement du championnat indisponible."
        )
        return

    st.caption(
        f"Cumul des points jusqu'à **{grand_prix}** "
        f"(manche {manches} de la saison {annee})."
    )

    progression = st.progress(0.0, text="Chargement des courses…")
    onglet_pilotes, onglet_constructeurs = st.tabs(["Pilotes", "Constructeurs"])
    zone_pilotes = onglet_pilotes.empty()
    zone_constructeurs = onglet_constructeurs.empty()
    note = st.empty()

    affiche = False
    for cumul, charge, total in points_par_course_progressif(annee, manches):
        progression.progress(
            min(charge / total, 1.0) if total else 1.0,
            text=f"Courses chargées : {charge}/{total}",
        )

        pilotes = agreger_classement_pilotes(cumul)
        if pilotes.empty:
            continue

        zone_pilotes.dataframe(pilotes, hide_index=True, width="stretch")
        zone_constructeurs.dataframe(
            agreger_classement_constructeurs(cumul), hide_index=True, width="stretch"
        )
        affiche = True

        if charge < total:
            note.caption(
                f"⏳ Classement partiel : {charge} manches sur {total}. "
                "Le tableau se complète à mesure du chargement."
            )

    progression.empty()

    if not affiche:
        note.info(
            "Aucun résultat de course exploitable pour cette saison. "
            "Les données paraissent quelques heures après chaque épreuve."
        )
        return

    note.caption(
        f"Points cumulés depuis les résultats de course OpenF1 : la source "
        f"Ergast, plus directe, ne couvre pas la saison {annee}."
    )


with t2:
    st.subheader("Championnat")

    if ergast_couvre(annee):
        # Ergast renvoie le classement en un seul appel : pas besoin de cumuler.
        ctab1, ctab2 = st.tabs(["Pilotes", "Constructeurs"])
        with ctab1:
            standings = calcul_classement_pilote(annee, grand_prix)
            if not standings.empty:
                st.dataframe(standings, hide_index=True, width="stretch")
            else:
                st.info("Classement pilotes indisponible (données incomplètes).")
        with ctab2:
            cstand = calcul_classement_constructeur(annee, grand_prix)
            if not cstand.empty:
                st.dataframe(cstand, hide_index=True, width="stretch")
            else:
                st.info("Classement constructeurs indisponible (données incomplètes).")
    else:
        _championnat_progressif(annee, grand_prix)
