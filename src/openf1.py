"""Client HTTP pour l'API OpenF1 (https://openf1.org).

Source de données de substitution à FastF1 : l'API Live Timing officielle
(`livetiming.formula1.com`) est injoignable depuis certains hébergements —
notamment Streamlit Cloud, dont les IP de datacenter sont refusées — ce qui
rendait l'application inutilisable en production.

Ce module ne dépend ni de Streamlit ni de FastF1 : il renvoie des structures
Python brutes (listes de dictionnaires). La conversion vers les DataFrames
attendus par l'application est faite dans `src.data`.

Toutes les requêtes réseau de l'application passent par ici : changer de
fournisseur de données ne demande de toucher qu'à ce fichier.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("f1_analytics.openf1")

BASE_URL = "https://api.openf1.org/v1"

# Première saison couverte par OpenF1 (vérifié : aucune donnée avant 2023).
PREMIERE_SAISON = 2023

_TIMEOUT = 30.0
_TENTATIVES = 3
_ATTENTE_ENTRE_TENTATIVES = 1.5

# OpenF1 limite le débit et répond 429 avec un en-tête `retry-after` (60 s
# observé). Le plafond évite qu'un quota mal annoncé ne fige l'application.
_ATTENTE_QUOTA_DEFAUT = 5.0
_ATTENTE_QUOTA_MAX = 20.0

# Pause entre deux requêtes de télémétrie (une par pilote, soit ~44 appels).
# Mesuré : en séquentiel espacé, 21 pilotes sur 22 obtiennent leur télémétrie
# en ~60 s ; avec 4 requêtes parallèles, le quota sature et il n'en reste que
# 17 pour 40 s. La complétude prime sur la vitesse, le résultat étant mis en
# cache 30 minutes.
DELAI_ENTRE_APPELS = 0.4


class OpenF1Error(RuntimeError):
    """Erreur d'accès à l'API OpenF1 (réseau, HTTP ou réponse illisible)."""


def _construire_url(endpoint: str, params: dict) -> str:
    """Assemble l'URL. Les opérateurs de comparaison sont préservés.

    OpenF1 filtre avec une syntaxe du type `date>=2026-07-19T13:00:00`. Un
    encodage classique casserait ces opérateurs : on les garde littéraux via
    `safe`, sinon l'API renvoie la session entière.
    """
    if not params:
        return f"{BASE_URL}/{endpoint}"
    morceaux = [
        f"{cle}={urllib.parse.quote(str(valeur), safe='>=<:+-T.')}"
        for cle, valeur in params.items()
        if valeur is not None
    ]
    return f"{BASE_URL}/{endpoint}?" + "&".join(morceaux)


def _get(endpoint: str, **params) -> list[dict]:
    """Interroge un endpoint OpenF1 et retourne la liste de résultats.

    Réessaie sur erreur réseau ou 5xx. Une réponse 404 est traduite en liste
    vide : elle signifie « pas de données pour ces critères », pas une panne.
    """
    url = _construire_url(endpoint, params)
    derniere: Exception | None = None

    for tentative in range(1, _TENTATIVES + 1):
        try:
            requete = urllib.request.Request(
                url, headers={"User-Agent": "f1-analytics", "Accept": "application/json"}
            )
            with urllib.request.urlopen(requete, timeout=_TIMEOUT) as reponse:
                charge = reponse.read().decode("utf-8")
            donnees = json.loads(charge)
            if isinstance(donnees, dict):
                # OpenF1 renvoie un objet (et non une liste) pour signaler une erreur.
                raise OpenF1Error(f"Réponse inattendue de {endpoint}: {donnees}")
            return donnees

        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                logger.info("OpenF1 %s: aucune donnée (404)", endpoint)
                return []
            derniere = exc
            if exc.code == 429:
                # Quota atteint : l'API indique le délai d'attente à respecter.
                # Sans cette pause, les requêtes suivantes échouent en cascade
                # et la télémétrie n'est récupérée que pour une partie des pilotes.
                attente = _ATTENTE_QUOTA_DEFAUT
                try:
                    attente = float(exc.headers.get("retry-after", attente))
                except (TypeError, ValueError):
                    pass
                attente = min(attente, _ATTENTE_QUOTA_MAX)
                if tentative < _TENTATIVES:
                    logger.warning(
                        "OpenF1 %s: quota atteint, attente de %.0f s", endpoint, attente
                    )
                    time.sleep(attente)
                continue
            if exc.code < 500:
                break  # autres 4xx : réessayer ne changera rien
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            derniere = exc

        if tentative < _TENTATIVES:
            logger.warning(
                "OpenF1 %s: tentative %d/%d échouée (%s)",
                endpoint, tentative, _TENTATIVES, type(derniere).__name__,
            )
            time.sleep(_ATTENTE_ENTRE_TENTATIVES * tentative)

    raise OpenF1Error(
        f"Impossible de joindre OpenF1 ({endpoint}): "
        f"{type(derniere).__name__}: {derniere}"
    ) from derniere


# ---------------------------------------------------------------------------
# Calendrier et résolution de session
# ---------------------------------------------------------------------------
# Types de session de l'application -> critères OpenF1.
_TYPES_SESSION = {
    "FP1": {"session_name": "Practice 1"},
    "FP2": {"session_name": "Practice 2"},
    "FP3": {"session_name": "Practice 3"},
    "Q": {"session_name": "Qualifying"},
    "R": {"session_name": "Race", "session_type": "Race"},
}


def sessions(annee: int, **filtres) -> list[dict]:
    """Sessions d'une saison, éventuellement filtrées."""
    return _get("sessions", year=annee, **filtres)


def courses(annee: int) -> list[dict]:
    """Grands Prix d'une saison, ordonnés par date — bâtit le calendrier.

    Filtre sur `session_name == "Race"` et non sur `session_type` : les Sprints
    portent eux aussi le type "Race", ce qui ferait apparaître deux fois les
    week-ends sprint dans le sélecteur.
    """
    resultats = _get("sessions", year=annee, session_name="Race")
    return sorted(
        [s for s in resultats if not s.get("is_cancelled")],
        key=lambda s: s.get("date_start") or "",
    )


def nom_grand_prix(session: dict) -> str:
    """Nom lisible et **unique** d'un Grand Prix à partir d'une session.

    OpenF1 ne fournit pas de libellé « Belgian Grand Prix ». Le nom est composé
    depuis le pays, mais celui-ci ne suffit pas : une saison compte jusqu'à
    trois Grands Prix aux États-Unis (Miami, Austin, Las Vegas) et deux en
    Italie ou en Espagne. On nomme donc par le lieu, qui est unique, en gardant
    le pays quand les deux coïncident (« Belgium Grand Prix »).
    """
    pays = session.get("country_name")
    lieu = session.get("location") or session.get("circuit_short_name")

    if lieu and pays and lieu.strip().lower() != pays.strip().lower():
        return f"{pays} Grand Prix ({lieu})"
    if pays:
        return f"{pays} Grand Prix"
    return f"{lieu or '?'} Grand Prix"


def trouver_session(annee: int, course: str, sess_type: str) -> dict | None:
    """Retrouve la session correspondant à (année, Grand Prix, type).

    `course` est le libellé produit par `nom_grand_prix`, tel qu'affiché dans
    le sélecteur.
    """
    criteres = _TYPES_SESSION.get(sess_type)
    if criteres is None:
        raise ValueError(f"Type de session inconnu: {sess_type}")

    candidates = _get("sessions", year=annee, **criteres)
    for session in candidates:
        if nom_grand_prix(session) == course:
            return session

    # Repli : rapprochement sur le lieu, extrait de « Pays Grand Prix (Lieu) »
    # ou du libellé simple. Tolère les anciens libellés mémorisés dans l'état
    # de session après un changement de format.
    reference = course
    if "(" in reference and reference.endswith(")"):
        reference = reference[reference.rindex("(") + 1: -1]
    reference = reference.replace(" Grand Prix", "").strip().lower()

    for session in candidates:
        for champ in ("location", "circuit_short_name", "country_name"):
            valeur = session.get(champ)
            if valeur and valeur.strip().lower() == reference:
                return session
    return None


# ---------------------------------------------------------------------------
# Données de session
# ---------------------------------------------------------------------------
def pilotes(session_key: int) -> list[dict]:
    """Pilotes engagés : numéro, acronyme, nom, équipe, couleur."""
    return _get("drivers", session_key=session_key)


def tours(session_key: int) -> list[dict]:
    """Tours de tous les pilotes : durée, secteurs, vitesses de passage."""
    return _get("laps", session_key=session_key)


def relais(session_key: int) -> list[dict]:
    """Relais (stints) : composé et âge du pneu, bornés par lap_start/lap_end."""
    return _get("stints", session_key=session_key)


def meteo(session_key: int) -> list[dict]:
    """Relevés météo horodatés."""
    return _get("weather", session_key=session_key)


def arrets(session_key: int) -> list[dict]:
    """Arrêts aux stands : durée et tour concerné."""
    return _get("pit", session_key=session_key)


def resultats(session_key: int) -> list[dict]:
    """Classement final : position, points, abandons."""
    return _get("session_result", session_key=session_key)


def positions(session_key: int) -> list[dict]:
    """Positions horodatées, pour suivre l'évolution de la course."""
    return _get("position", session_key=session_key)


# ---------------------------------------------------------------------------
# Télémétrie
# ---------------------------------------------------------------------------
def telemetrie_tour(
    session_key: int,
    driver_number: int,
    date_debut: str,
    date_fin: str,
) -> tuple[list[dict], list[dict]]:
    """Télémétrie et position d'un pilote sur une fenêtre temporelle.

    Le filtrage par dates est **essentiel** : `car_data` non filtré pèse ~5,5 Mo
    par pilote (~120 Mo pour une grille complète), contre ~90 Ko sur la fenêtre
    d'un tour.

    Retour
    ------
    (car_data, location) — deux listes d'enregistrements horodatés.
    """
    fenetre = {"date>": date_debut, "date<": date_fin}
    car = _get("car_data", session_key=session_key,
               driver_number=driver_number, **fenetre)
    pos = _get("location", session_key=session_key,
               driver_number=driver_number, **fenetre)
    return car, pos
