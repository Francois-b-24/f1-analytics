"""Chargement de session avec gestion d'erreur unifiée pour toutes les pages.

Avant ce module, seul l'accueil traitait les échecs de chargement : les dix
pages appelaient `chargement_session` à nu. Arriver sur une page par lien direct
pendant une panne OpenF1 affichait donc une traceback brute.

Le triage repose sur les types d'exception de `src.openf1`, pas sur une
inspection du texte du message : `OpenF1Indisponible` (réessayer a du sens) et
`OpenF1SansDonnees` (réessayer est inutile) appellent deux messages distincts.
"""
from __future__ import annotations

import logging
import traceback

import streamlit as st

from .openf1 import OpenF1Indisponible, OpenF1SansDonnees

logger = logging.getLogger("f1_analytics.session")


def charger_session_ou_stopper(annee: int, grand_prix: str, session_type: str) -> dict:
    """Charge une session, ou affiche un message exploitable et arrête la page.

    Retourne le dict de session (contrat de `chargement_session`) ou bien ne
    retourne jamais : en cas d'échec, la fonction rend un message, un bouton
    « Réessayer », les détails techniques, puis appelle `st.stop()`.

    L'import de `chargement_session` est volontairement fait **dans le corps**
    de la fonction : un import au niveau module copierait la référence dans ce
    namespace et rendrait inopérant tout `monkeypatch` de
    `src.data.chargement_session` dans les tests de rendu. Même motif que
    `src.ui`, qui importe `openf1` paresseusement.
    """
    from .data import chargement_session

    try:
        return chargement_session(annee, grand_prix, session_type)
    except OpenF1SansDonnees as exc:
        logger.info("Session sans données %s / %s / %s : %s",
                    annee, grand_prix, session_type, exc)
        st.error(
            f"❌ Pas de données pour {annee} – {grand_prix} ({session_type}). "
            "Cette session n'a pas encore eu lieu, ou ses données ne sont pas "
            "encore publiées (comptez quelques heures après la séance)."
        )
        _details_techniques(exc)
        st.stop()
    except OpenF1Indisponible as exc:
        logger.warning("OpenF1 injoignable %s / %s / %s : %s",
                       annee, grand_prix, session_type, exc)
        st.error(
            "🔌 L'API F1 est momentanément injoignable. "
            "Réessayez dans quelques instants."
        )
        _bouton_reessayer()
        _details_techniques(exc)
        st.stop()
    except Exception as exc:
        logger.exception("Échec chargement session %s / %s / %s",
                         annee, grand_prix, session_type)
        st.error(
            f"⚠️ Impossible de charger cette session : "
            f"**{type(exc).__name__}** — {exc or '(pas de message)'}"
        )
        _bouton_reessayer()
        _details_techniques(exc)
        st.stop()


def _bouton_reessayer() -> None:
    """Bouton vidant le cache de session avant de relancer le chargement."""
    from .data import chargement_session

    col, _ = st.columns([1, 4])
    with col:
        if st.button("🔄 Réessayer", key="retry_load"):
            chargement_session.clear()
            st.rerun()


def _details_techniques(exc: BaseException) -> None:
    """Trace complète, repliée — utile pour diagnostiquer sans alourdir l'écran."""
    with st.expander("Détails techniques"):
        st.code(f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}")
