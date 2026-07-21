from __future__ import annotations

import logging
import time

import pandas as pd
import streamlit as st
from . import adaptateurs, openf1
from .theme import CATEGORIQUE, couleur_pilote
from .utils import formatage_timedelta
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from matplotlib.collections import LineCollection

logger = logging.getLogger("f1_analytics.data")


def _err_figure(msg: str, *, figsize=(12, 6.75), dpi=100):
    """Crée une figure matplotlib unique qui affiche un message d'erreur lisible.

    Thème sombre cohérent avec l'app — texte clair sur fond anthracite.
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.text(0.5, 0.5, msg, ha="center", va="center",
            color="#e6edf3", fontsize=12, wrap=True)
    ax.axis("off")
    return fig


def _safe_figure(fn):
    """Décorateur : enveloppe une fonction de génération de figure dans un
    try/except global qui retourne une `_err_figure` lisible au lieu de
    crasher la page Streamlit. Log la trace complète via logger.exception.
    """
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.exception("Échec de %s", fn.__name__)
            return _err_figure(
                f"Erreur lors du rendu : {type(exc).__name__}\n{exc}",
                figsize=kwargs.get("figsize", (12, 6.75)),
                dpi=kwargs.get("dpi", 100),
            )

    return wrapper

def _extraire_telemetrie_openf1(session_key: int, tours: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Récupère la télémétrie du meilleur tour de chaque pilote.

    Une requête par pilote, bornée à la fenêtre temporelle de son meilleur tour :
    la télémétrie non filtrée pèse ~5,5 Mo par pilote (~120 Mo pour la grille),
    contre ~90 Ko sur un seul tour.
    """
    if tours.empty or "IsPersonalBest" not in tours.columns:
        return {}

    meilleurs = tours[tours["IsPersonalBest"] & tours["LapSeconds"].notna()]

    def _charger(tour) -> tuple[str, pd.DataFrame] | None:
        code = tour.get("Driver")
        debut = tour.get("DateDebut")
        duree = tour.get("LapSeconds")
        numero = tour.get("DriverNumber")
        if not code or not debut or pd.isna(duree) or pd.isna(numero):
            return None
        try:
            fin = pd.to_datetime(debut, format="ISO8601", utc=True) + pd.Timedelta(seconds=float(duree))
            car, pos = openf1.telemetrie_tour(
                session_key, int(numero), debut, fin.isoformat()
            )
            tel = adaptateurs.construire_telemetrie(car, pos)
            return (code, tel) if not tel.empty else None
        except Exception as exc:
            logger.warning("Télémétrie indisponible pour %s: %s: %s",
                           code, type(exc).__name__, exc)
            return None

    # Séquentiel espacé plutôt que parallèle : mesuré sur une grille complète,
    # 4 requêtes simultanées saturent le quota OpenF1 et ne ramènent que 17
    # pilotes sur 22, contre 21 en séquentiel. Le gain de temps ne compense pas
    # la perte de données, d'autant que le résultat est mis en cache 30 min.
    resultat: dict[str, pd.DataFrame] = {}
    for rang, (_, tour) in enumerate(meilleurs.iterrows()):
        if rang:
            time.sleep(openf1.DELAI_ENTRE_APPELS)
        issue = _charger(tour)
        if issue is not None:
            resultat[issue[0]] = issue[1]
    return resultat


@st.cache_data(show_spinner="Chargement de la session F1…", max_entries=2, ttl=1800)
def _chargement_dataframes(annee: int, course: str, sess_type: str, _v: int = 6):
    """Charge tous les DataFrames d'une session depuis OpenF1.

    L'API Live Timing officielle est inaccessible depuis certains hébergements
    (IP de datacenter refusées) : OpenF1 sert donc de source de données. Le
    contrat de retour est inchangé, les pages n'ont pas à le savoir.

    _v : version interne pour invalider le cache en cas de changement de schéma.
    """
    session = openf1.trouver_session(annee, course, sess_type)
    if session is None:
        raise RuntimeError(
            f"Session introuvable : {annee} – {course} ({sess_type}). "
            "Elle n'a peut-être pas encore eu lieu, ou n'est pas publiée."
        )

    session_key = session["session_key"]
    logger.info("Chargement OpenF1 %s / %s / %s (session_key=%s)",
                annee, course, sess_type, session_key)

    pilotes_bruts = openf1.pilotes(session_key)
    tours = adaptateurs.construire_tours(
        openf1.tours(session_key),
        pilotes_bruts,
        openf1.relais(session_key),
        openf1.arrets(session_key),
    )
    if tours.empty:
        raise RuntimeError(
            f"Aucun tour disponible pour {annee} – {course} ({sess_type}). "
            "Les données paraissent quelques heures après la session."
        )

    # Positions par tour : nécessaires au graphique d'évolution (page
    # Performances) et n'existent que pour les courses.
    try:
        tours = adaptateurs.ajouter_positions(tours, openf1.positions(session_key))
    except Exception as exc:
        logger.info("Positions par tour indisponibles: %s", exc)

    driver_codes = sorted(tours["Driver"].dropna().unique().tolist())

    try:
        meteo = adaptateurs.construire_meteo(
            openf1.meteo(session_key), session.get("date_start")
        )
    except Exception as exc:
        logger.info("Données météo indisponibles: %s", exc)
        meteo = pd.DataFrame()

    try:
        resultats = adaptateurs.construire_resultats(
            openf1.resultats(session_key), pilotes_bruts
        )
    except Exception as exc:
        logger.info("Résultats officiels indisponibles: %s", exc)
        resultats = pd.DataFrame()

    tel_par_pilote = _extraire_telemetrie_openf1(session_key, tours)

    best_laps: dict[str, dict] = {}
    for _, tour in tours[tours.get("IsPersonalBest", False)].iterrows():
        code = tour.get("Driver")
        if code:
            best_laps[code] = {
                "LapTime": tour.get("LapTime"),
                "LapNumber": int(tour["LapNumber"]) if pd.notna(tour.get("LapNumber")) else None,
            }

    logger.info("Session chargée: %d tours, %d pilotes, %d avec télémétrie",
                len(tours), len(driver_codes), len(tel_par_pilote))
    return dict(
        nom=session.get("session_name") or sess_type,
        tours=tours,
        pilotes=driver_codes,
        meteo=meteo,
        resultats=resultats,
        tel_par_pilote=tel_par_pilote,
        best_laps=best_laps,
        session_key=session_key,
    )


def chargement_session(annee: int, course: str, sess_type: str):
    """
    Charge une session F1 et retourne ses données.

    Les données proviennent d'OpenF1 et sont mises en cache par `cache_data`.
    Tout est renvoyé sous forme de DataFrames : il n'y a plus d'objet Session
    vivant à maintenir, ce qui supprime à la fois les DataNotLoadedError et
    l'empreinte mémoire de ~600 Mo par session.

    Paramètres
    ----------
    annee : int
    course : str
        Nom du Grand Prix tel qu'affiché dans le sélecteur
        (ex: "Belgium Grand Prix", "United States Grand Prix (Austin)").
    sess_type : str
        "FP1", "FP2", "FP3", "Q", "R".

    Retour
    ------
    dict
        - nom : nom de la session
        - tours : DataFrame des tours
        - pilotes : liste des codes pilotes
        - meteo : DataFrame météo
        - resultats : DataFrame résultats officiels
        - tel_par_pilote : {code pilote: DataFrame de télémétrie}
        - best_laps : {code pilote: {LapTime, LapNumber}}
        - session_key : identifiant OpenF1 de la session
        - session : None — conservé pour compatibilité des appels existants
    """
    dfs = _chargement_dataframes(annee, course, sess_type)
    return {**dfs, "session": None}


# Expose .clear() comme avant pour Home.py (bouton "Réessayer")
chargement_session.clear = _chargement_dataframes.clear

def tour_rapide_tel(data: dict, code_pilote: str):
    """
    Retourne les infos du meilleur tour et sa télémétrie pour un pilote.

    Utilise les données pré-extraites dans `data` (retour de
    `chargement_session`) — plus aucun accès à `lap.session` ou
    `Session.car_data`, ce qui évitait le DataNotLoadedError persistant.

    Paramètres
    ----------
    data : dict
        Retour de `chargement_session` (contient `tel_par_pilote`, `best_laps`).
    code_pilote : str
        Code 3-lettres (ex: "HAM", "VER").

    Retour
    ------
    tuple[dict, pd.DataFrame]
        (infos meilleur tour {LapTime, LapNumber}, DataFrame télémétrie).

    Raises
    ------
    ValueError
        Si aucune télémétrie disponible pour ce pilote.
    """
    tel_par_pilote = data.get("tel_par_pilote", {})
    best_laps = data.get("best_laps", {})

    tel = tel_par_pilote.get(code_pilote)
    if tel is None or len(tel) == 0:
        raise ValueError(f"Télémétrie indisponible pour {code_pilote}")

    best = best_laps.get(code_pilote, {})
    return best, tel

def _round_upto(annee: int, upto_event: str) -> int | None:
    """Numéro de manche (1-based) correspondant à `upto_event`.

    Le calendrier vient d'OpenF1 : les libellés doivent correspondre à ceux du
    sélecteur, et l'ancien appel à `fastf1.get_event_schedule` reposait sur
    l'API Live Timing, inaccessible depuis l'hébergement.
    """
    try:
        courses = openf1.courses(annee)
    except Exception as exc:
        logger.warning("Calendrier %s indisponible: %s", annee, exc)
        return None

    noms = [openf1.nom_grand_prix(c) for c in courses]
    if upto_event not in noms:
        return None
    return noms.index(upto_event) + 1


def _points_par_course(annee: int, nb_manches: int) -> pd.DataFrame:
    """Points marqués course par course, jusqu'à la manche `nb_manches`.

    Sert de repli quand Ergast est indisponible. Interroge OpenF1 plutôt que
    de recharger chaque session FastF1 : l'API Live Timing est inaccessible
    depuis l'hébergement, et un chargement complet par course serait lourd.

    Retour
    ------
    DataFrame : BroadcastName, TeamName, Points. Vide si rien d'exploitable.
    """
    try:
        courses = openf1.courses(annee)[:nb_manches]
    except Exception as exc:
        logger.warning("Calendrier %s indisponible: %s", annee, exc)
        return pd.DataFrame()

    morceaux = []
    for course in courses:
        cle = course.get("session_key")
        if cle is None:
            continue
        try:
            resultats = adaptateurs.construire_resultats(
                openf1.resultats(cle), openf1.pilotes(cle)
            )
        except Exception as exc:
            logger.debug("Résultats indisponibles (session %s): %s", cle, exc)
            continue
        if not resultats.empty and {"BroadcastName", "TeamName", "Points"} <= set(resultats.columns):
            morceaux.append(resultats[["BroadcastName", "TeamName", "Points"]])

    if not morceaux:
        return pd.DataFrame()

    points = pd.concat(morceaux, ignore_index=True)
    points["Points"] = pd.to_numeric(points["Points"], errors="coerce").fillna(0)
    return points


def _ergast() -> "object | None":
    """Retourne une instance Ergast si disponible, sinon None."""
    try:
        from fastf1.ergast import Ergast
        return Ergast()
    except Exception as exc:
        logger.info("Ergast indisponible: %s", exc)
        return None


@st.cache_data(ttl=3600, show_spinner="Calcul du classement pilotes…", max_entries=8)
def calcul_classement_pilote(annee: int, upto_event: str) -> pd.DataFrame:
    """
    Calcule le classement cumulé des pilotes jusqu'à un événement donné.

    Utilise l'API Ergast (intégrée à FastF1) au lieu de boucler sur
    `sess.load()` de chaque course — 1 appel HTTP léger vs N téléchargements lourds.

    Retour
    ------
    pd.DataFrame
        Colonnes : Position, BroadcastName, TeamName, Points.
        DataFrame vide si données indisponibles.
    """
    rnd = _round_upto(annee, upto_event)
    if rnd is None:
        return pd.DataFrame()

    erg = _ergast()
    if erg is not None:
        try:
            resp = erg.get_driver_standings(season=annee, round=rnd)
            if resp.content:
                df = resp.content[0]
                df = df.assign(
                    BroadcastName=(df['givenName'].str.upper().str[0] + '. ' + df['familyName'].str.upper()),
                    TeamName=df['constructorNames'].apply(lambda x: x[0] if isinstance(x, list) and x else None),
                    Points=pd.to_numeric(df['points'], errors='coerce').fillna(0).astype(int),
                    Position=pd.to_numeric(df['position'], errors='coerce').fillna(0).astype(int),
                )
                return df[['Position', 'BroadcastName', 'TeamName', 'Points']].reset_index(drop=True)
        except Exception as exc:
            logger.warning("Ergast driver_standings a échoué, fallback session-par-session: %s", exc)

    # Repli : cumuler les points course par course depuis OpenF1.
    points = _points_par_course(annee, rnd)
    if points.empty:
        return pd.DataFrame()

    classement = (points.groupby(["BroadcastName", "TeamName"], dropna=False)["Points"]
                  .sum().reset_index())
    standings = classement.sort_values("Points", ascending=False).reset_index(drop=True)
    standings["Position"] = standings.index + 1
    return standings[["Position", "BroadcastName", "TeamName", "Points"]]


@st.cache_data(ttl=3600, show_spinner="Calcul du classement constructeurs…", max_entries=8)
def calcul_classement_constructeur(annee: int, upto_event: str) -> pd.DataFrame:
    """
    Calcule le classement cumulé des constructeurs jusqu'à un événement donné.

    Utilise Ergast (1 appel léger) avec fallback sur les résultats par course
    (sans charger laps/telemetry).

    Retour
    ------
    pd.DataFrame
        Colonnes : Position, TeamName, Points.
    """
    rnd = _round_upto(annee, upto_event)
    if rnd is None:
        return pd.DataFrame()

    erg = _ergast()
    if erg is not None:
        try:
            resp = erg.get_constructor_standings(season=annee, round=rnd)
            if resp.content:
                df = resp.content[0]
                df = df.assign(
                    TeamName=df['constructorName'],
                    Points=pd.to_numeric(df['points'], errors='coerce').fillna(0).astype(int),
                    Position=pd.to_numeric(df['position'], errors='coerce').fillna(0).astype(int),
                )
                return df[['Position', 'TeamName', 'Points']].reset_index(drop=True)
        except Exception as exc:
            logger.warning("Ergast constructor_standings a échoué, fallback: %s", exc)

    points = _points_par_course(annee, rnd)
    if points.empty:
        return pd.DataFrame()

    classement = (points.groupby(["TeamName"], dropna=False)["Points"]
                  .sum().reset_index())
    standings = classement.sort_values("Points", ascending=False).reset_index(drop=True)
    standings["Position"] = standings.index + 1
    return standings[["Position", "TeamName", "Points"]]

def classement_session(nb_tours: pd.DataFrame, results_df: pd.DataFrame, sess_type: str) -> pd.DataFrame:
    """
    Calcule le classement d'une session donnée.
    
    Paramètres
    ----------
    nb_tours : pd.DataFrame
        DataFrame contenant les tours de la session.
    results_df : pd.DataFrame
        DataFrame contenant les résultats officiels (si disponibles).
    sess_type : str
        Type de session ("FP1", "FP2", "FP3", "Q", "R").
    
    Retour
    ------
    pd.DataFrame
        DataFrame du classement avec colonnes selon le type de session.
        DataFrame vide si données insuffisantes.
    """
    if sess_type == 'R' and not results_df.empty and 'Position' in results_df:
        cols = [c for c in ["Position","BroadcastName","DriverNumber","TeamName","TeamColor","Points","Status","Time","FastestLapTime"] if c in results_df.columns]
        df = results_df[cols].copy()
        for c in ["Time","FastestLapTime"]:
            if c in df.columns:
                try:
                    df[c] = df[c].apply(formatage_timedelta)
                except Exception:
                    pass
        return df.sort_values('Position').reset_index(drop=True)

    if 'Driver' not in nb_tours or 'LapTime' not in nb_tours:
        return pd.DataFrame()
    tmp = (nb_tours.dropna(subset=['Driver','LapTime'])
                  .groupby('Driver', as_index=False)
                  .agg(BestLapTime=('LapTime','min'),
                       BestLapNo=('LapNumber','min')))
    tmp['BestLapStr'] = tmp['BestLapTime'].apply(formatage_timedelta)
    if 'Team' in nb_tours.columns:
        team_map = nb_tours.dropna(subset=['Driver']).drop_duplicates('Driver').set_index('Driver')['Team'].to_dict()
        tmp['Team'] = tmp['Driver'].map(team_map)
    tmp = tmp.sort_values('BestLapTime').reset_index(drop=True)
    tmp['Position'] = tmp.index + 1
    return tmp[['Position','Driver','Team','BestLapNo','BestLapStr'] if 'Team' in tmp.columns else ['Position','Driver','BestLapNo','BestLapStr']]



@_safe_figure
def figure_positions_par_tour(tours: pd.DataFrame, pilotes=None):
    """Trace l'évolution de la position de chaque pilote au fil des tours.

    Paramètres
    ----------
    tours : pd.DataFrame
        DataFrame `tours` de `chargement_session`, avec les colonnes
        Driver, LapNumber et Position.
    pilotes : list[str] | None
        Codes pilotes à tracer. Si None, tous ceux présents.

    Retour
    ------
    matplotlib.figure.Figure
    """
    if tours is None or len(tours) == 0:
        return _err_figure("Aucun tour dans cette session", figsize=(10, 5))

    manquantes = {"Driver", "LapNumber", "Position"} - set(tours.columns)
    if manquantes:
        return _err_figure(
            "Colonnes manquantes : " + ", ".join(sorted(manquantes)) + ".\n"
            "Cette visualisation n'est disponible que pour les courses (R).",
            figsize=(10, 5),
        )

    valides = tours.dropna(subset=["Position"])
    if valides.empty:
        return _err_figure(
            "Aucune donnée de position — cette visualisation ne concerne que les courses (R).",
            figsize=(10, 5),
        )

    if pilotes is None:
        pilotes = sorted(valides["Driver"].dropna().unique().tolist())
    if not pilotes:
        return _err_figure("Aucun pilote détecté dans les tours", figsize=(10, 5))

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.tick_params(colors="#e6edf3")
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")
    ax.xaxis.label.set_color("#e6edf3")
    ax.yaxis.label.set_color("#e6edf3")
    ax.title.set_color("#e6edf3")
    ax.grid(True, color="#21262d", linewidth=0.5, alpha=0.7)

    nb_trace = 0
    for rang, code in enumerate(pilotes):
        lignes = valides[valides["Driver"] == code].sort_values("LapNumber")
        if lignes.empty:
            continue
        # Palette validée du thème, et trait alterné au-delà de 8 pilotes pour
        # que deux séries de même couleur restent distinguables.
        ax.plot(
            lignes["LapNumber"], lignes["Position"],
            label=code, linewidth=1.6,
            color=couleur_pilote(rang),
            linestyle=["-", "--", ":"][(rang // len(CATEGORIQUE)) % 3],
        )
        nb_trace += 1

    if nb_trace == 0:
        plt.close(fig)
        return _err_figure(
            "Aucune position n'a pu être tracée — vérifie que c'est bien une course (R).",
            figsize=(10, 5),
        )

    # Bornes dérivées de la grille réelle (22 voitures en 2026, 20 auparavant).
    try:
        nb_positions = int(valides["Position"].max())
    except (ValueError, TypeError):
        nb_positions = 0
    if nb_positions < 1:
        nb_positions = max(len(pilotes), 20)

    ax.set_ylim([nb_positions + 0.5, 0.5])
    ticks = [1] + list(range(5, nb_positions + 1, 5))
    if ticks[-1] != nb_positions:
        ticks.append(nb_positions)
    ax.set_yticks(ticks)
    ax.set_xlabel("Tour")
    ax.set_ylabel("Position")
    leg = ax.legend(
        bbox_to_anchor=(1.02, 1.0), loc="upper left", title="Pilotes",
        fontsize=8, frameon=False, labelcolor="#e6edf3",
    )
    if leg is not None:
        leg.get_title().set_color("#e6edf3")
    plt.tight_layout()

    return fig


@_safe_figure
def figure_carte_vitesse(tel: pd.DataFrame,
                         cmap=mpl.cm.plasma,
                         figsize=(12, 6.75),
                         dpi=100,
                         linewidth_track: float = 16,
                         linewidth_speed: float = 5,
                         show_colorbar: bool = True):
    """
    Crée et renvoie une figure Matplotlib : visualisation de la vitesse sur la trajectoire.

    Paramètres
    ----------
    tel : pd.DataFrame
        Télémétrie d'un tour (colonnes X, Y et Speed), telle que fournie par
        `chargement_session` dans `tel_par_pilote`.
    cmap : matplotlib colormap
        Colormap utilisée (par défaut plasma).
    figsize : tuple[float, float]
        Taille de la figure en pouces.
    dpi : int
        Résolution de la figure.
    linewidth_track : float
        Épaisseur de la ligne de fond (piste).
    linewidth_speed : float
        Épaisseur de la ligne colorée par la vitesse.
    show_colorbar : bool
        Afficher la barre de couleurs.

    Retour
    ------
    matplotlib.figure.Figure
    """
    if tel is None or len(tel) == 0:
        return _err_figure("Télémétrie vide", figsize=figsize, dpi=dpi)
    if not all(c in tel.columns for c in ("X", "Y", "Speed")):
        return _err_figure("Colonnes X/Y/Speed manquantes", figsize=figsize, dpi=dpi)

    x = np.asarray(tel['X'], dtype=float)
    y = np.asarray(tel['Y'], dtype=float)
    speed = np.asarray(tel['Speed'], dtype=float)

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    fig, ax = plt.subplots(sharex=True, sharey=True, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')
    ax.axis('off')

    ax.plot(x, y, color='#30363d', linewidth=linewidth_track, zorder=0)
    norm = plt.Normalize(speed.min(), speed.max())
    lc = LineCollection(segments, cmap=cmap, norm=norm, linewidth=linewidth_speed)
    lc.set_array(speed)
    ax.add_collection(lc)
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y.min(), y.max())
    ax.set_aspect('equal')

    if show_colorbar:
        cbaxes = fig.add_axes([0.25, 0.05, 0.5, 0.04])
        cb = mpl.colorbar.ColorbarBase(cbaxes,
                                       norm=mpl.colors.Normalize(speed.min(), speed.max()),
                                       cmap=cmap, orientation="horizontal")
        cb.set_label("Vitesse (km/h)", color="#e6edf3")
        cb.ax.tick_params(colors="#e6edf3")
        cb.outline.set_edgecolor("#30363d")
    return fig


# --- Visualisation des rapports engagés (nGear) ---
@_safe_figure
def figure_carte_rapports(tel: pd.DataFrame,
                           cmap=None,
                           figsize=(12, 6.75),
                           dpi=100,
                           linewidth_track: float = 16,
                           linewidth_gears: float = 4,
                           show_colorbar: bool = True):
    """Visualisation des rapports engagés le long de la trajectoire.

    Paramètres
    ----------
    tel : pd.DataFrame
        Télémétrie pré-extraite (colonnes X, Y, nGear).
    """
    if cmap is None:
        cmap = mpl.colormaps['Paired']

    if tel is None or len(tel) == 0:
        return _err_figure("Télémétrie vide", figsize=figsize, dpi=dpi)
    if not all(c in tel.columns for c in ("X", "Y", "nGear")):
        return _err_figure("Colonnes X/Y/nGear manquantes", figsize=figsize, dpi=dpi)

    x = np.asarray(tel['X'], dtype=float)
    y = np.asarray(tel['Y'], dtype=float)
    gear = np.asarray(tel['nGear'], dtype=float)

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    fig, ax = plt.subplots(sharex=True, sharey=True, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    ax.plot(x, y, color='#30363d', linewidth=linewidth_track, zorder=0)
    lc = LineCollection(segments, norm=plt.Normalize(1, cmap.N + 1), cmap=cmap, linewidth=linewidth_gears)
    lc.set_array(gear)
    ax.add_collection(lc)
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y.min(), y.max())
    ax.set_aspect('equal')
    ax.axis('off')

    if show_colorbar:
        cbar = plt.colorbar(mappable=lc, ax=ax, boundaries=np.arange(1, 10), fraction=0.046, pad=0.04)
        cbar.set_ticks(np.arange(1.5, 9.5))
        cbar.set_ticklabels(np.arange(1, 9))
        cbar.set_label("Rapport", color="#e6edf3")
        cbar.ax.tick_params(colors="#e6edf3")
        cbar.outline.set_edgecolor("#30363d")
    return fig


