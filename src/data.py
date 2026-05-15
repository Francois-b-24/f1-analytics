from __future__ import annotations

import logging

import pandas as pd
import streamlit as st
import fastf1
from .utils import secs, formatage_timedelta
import matplotlib.pyplot as plt
import fastf1.plotting
import numpy as np
import matplotlib as mpl
from matplotlib.collections import LineCollection

logger = logging.getLogger("f1_analytics.data")


def _select_lap(laps, lap_number: int | None):
    """
    Sélectionne un objet `fastf1.core.Lap` (pas une pd.Series) depuis un
    DataFrame de tours FastF1.

    Garantit que `get_telemetry()` / `get_pos_data()` sont appelables sur
    le retour — fait un `.iloc[[0]].pick_fastest()` plutôt que `.iloc[0]`
    qui renverrait une Series sans ces méthodes.

    Retourne `None` si rien d'utilisable (le caller doit gérer ce cas).
    """
    if laps is None or len(laps) == 0:
        return None

    # 1. Cas tour spécifique
    if lap_number is not None:
        try:
            subset = laps[laps["LapNumber"] == lap_number]
            if subset is not None and len(subset) > 0:
                lap = subset.pick_fastest()
                if lap is not None and hasattr(lap, "get_telemetry"):
                    return lap
        except Exception as exc:
            logger.debug("pick_fastest(subset lap_number=%s) a échoué: %s", lap_number, exc)

    # 2. Tour le plus rapide global
    try:
        # Filtrer d'abord les tours avec un LapTime valide (sinon pick_fastest peut renvoyer NaN/Series)
        if "LapTime" in laps.columns:
            valid = laps[laps["LapTime"].notna()]
            if len(valid) > 0:
                lap = valid.pick_fastest()
                if lap is not None and hasattr(lap, "get_telemetry"):
                    return lap
        lap = laps.pick_fastest()
        if lap is not None and hasattr(lap, "get_telemetry"):
            return lap
    except Exception as exc:
        logger.warning("pick_fastest(laps) a échoué: %s", exc)

    # 3. Fallback : récupérer la première ligne avec LapTime non-null
    try:
        if "LapTime" in laps.columns:
            valid = laps[laps["LapTime"].notna()]
            if len(valid) > 0:
                # `.iloc[[0]].pick_fastest()` retourne bien un Lap, pas une Series
                lap = valid.iloc[[0]].pick_fastest()
                if lap is not None and hasattr(lap, "get_telemetry"):
                    return lap
    except Exception as exc:
        logger.warning("fallback _select_lap a échoué: %s", exc)

    return None


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

def _session_telemetry_ready(sess) -> bool:
    """Vérifie qu'une session FastF1 a bien ses données télémétrie chargées.

    FastF1 utilise `hasattr(sess, '_car_data')` / `'_pos_data'` comme garde
    interne pour `Session.car_data` / `Session.pos_data`. Si l'un manque,
    `lap.get_car_data()` ou `lap.get_pos_data()` lèvent DataNotLoadedError.

    On vérifie les DEUX attributs car ils sont chargés ensemble par
    `_load_telemetry`.
    """
    return hasattr(sess, "_car_data") and hasattr(sess, "_pos_data")


def _ensure_session_loaded(sess) -> None:
    """Si la session a perdu ses attributs télémétrie, recharge en place.

    `sess.load()` est idempotente et utilise le cache disque FastF1, donc
    rapide (lecture des .ff1pkl locaux).
    """
    if _session_telemetry_ready(sess):
        return
    logger.info("Session sans télémétrie en mémoire — rechargement en place")
    sess.load()


def _build_session(annee: int, course: str, sess_type: str):
    """Crée et charge une session FastF1 fraîche (non cachée)."""
    logger.info("Chargement session %s / %s / %s", annee, course, sess_type)
    sess = fastf1.get_session(annee, course, sess_type)
    sess.load()  # laps + telemetry + weather + messages (par défaut)
    return sess


def _get_or_reload_session(annee: int, course: str, sess_type: str):
    """Renvoie un objet Session live avec télémétrie garantie chargée.

    Stockage par utilisateur dans `st.session_state` (pas inter-utilisateurs
    comme cache_resource). Si la session existe mais a perdu ses attributs
    `_car_data` / `_pos_data` (Streamlit peut wrapper l'objet entre runs),
    on rappelle `sess.load()` qui repeuple en mémoire depuis le cache disque.
    """
    key = f"_f1_sess_{annee}_{course}_{sess_type}"
    sess = st.session_state.get(key)
    if sess is None:
        sess = _build_session(annee, course, sess_type)
        st.session_state[key] = sess
        return sess
    # Session présente : s'assurer que la télémétrie est en mémoire
    try:
        _ensure_session_loaded(sess)
    except Exception as exc:
        logger.warning("Reload en place a échoué (%s), rebuild complet", exc)
        sess = _build_session(annee, course, sess_type)
        st.session_state[key] = sess
    return sess


@st.cache_data(show_spinner="Chargement de la session F1…", max_entries=4, ttl=3600)
def _chargement_dataframes(annee: int, course: str, sess_type: str):
    """Charge les DataFrames sérialisables (tours, météo, résultats).

    Ces données sont stables et cachables proprement par Streamlit
    (pickle DataFrame). L'objet Session live, lui, est obtenu séparément
    via `_get_or_reload_session` pour éviter les pertes d'attributs.
    """
    sess = _build_session(annee, course, sess_type)

    tours = sess.laps.copy().reset_index(drop=True)
    if 'LapTime' in tours:
        tours['LapSeconds'] = tours['LapTime'].apply(secs)
    for col in ['Sector1Time', 'Sector2Time', 'Sector3Time']:
        if col in tours:
            tours[col + 'Sec'] = tours[col].apply(secs)

    driver_codes = sorted(tours['Driver'].dropna().unique().tolist())

    try:
        meteo = sess.weather_data.copy().reset_index(drop=True)
        if 'Time' in meteo:
            meteo['SessionTimeSec'] = meteo['Time'].apply(secs)
    except Exception as exc:
        logger.info("Données météo indisponibles: %s", exc)
        meteo = pd.DataFrame()

    try:
        results = sess.results.copy().reset_index(drop=True)
    except Exception as exc:
        logger.info("Résultats officiels indisponibles: %s", exc)
        results = pd.DataFrame()

    nom = sess.name
    # On garde la session en session_state pour réutilisation par les viz
    key = f"_f1_sess_{annee}_{course}_{sess_type}"
    st.session_state[key] = sess

    logger.info("Session chargée: %d tours, %d pilotes", len(tours), len(driver_codes))
    return dict(
        nom=nom,
        tours=tours,
        pilotes=driver_codes,
        meteo=meteo,
        resultats=results,
    )


def chargement_session(annee: int, course: str, sess_type: str):
    """
    Charge une session F1 et retourne ses données.

    Les DataFrames (tours, météo, résultats) sont cachés via `cache_data`
    pour rapidité. L'objet Session live est récupéré séparément depuis
    `st.session_state` (ou rechargé depuis le cache disque FastF1 si nécessaire)
    pour préserver l'accès à `get_pos_data()`, `get_car_data()`, etc.

    Paramètres
    ----------
    annee : int
    course : str
        Nom du Grand Prix (ex: "Australian Grand Prix").
    sess_type : str
        "FP1", "FP2", "FP3", "Q", "R".

    Retour
    ------
    dict
        - session : objet Session FastF1 (toujours frais)
        - nom : nom de la session
        - tours : DataFrame des tours
        - pilotes : liste des codes pilotes
        - meteo : DataFrame météo
        - resultats : DataFrame résultats officiels
    """
    dfs = _chargement_dataframes(annee, course, sess_type)
    sess = _get_or_reload_session(annee, course, sess_type)
    return {**dfs, "session": sess}


# Expose .clear() comme avant pour Home.py (bouton "Réessayer")
chargement_session.clear = _chargement_dataframes.clear

def tour_rapide_tel(_sess, code_pilote: str):
    """
    Obtient le tour le plus rapide d'un pilote et sa télémétrie.

    IMPORTANT : prend l'objet Session FastF1 (pas un DataFrame détaché),
    car `Lap.get_car_data()` a besoin du pointeur vers la session pour
    accéder à `session.car_data` chargé en mémoire. Passer un DataFrame
    copié (sess.laps.copy().reset_index()) brise ce lien et lève
    `DataNotLoadedError`.

    Paramètres
    ----------
    _sess : fastf1.core.Session
        Session FastF1 chargée. Le préfixe `_` désactive le hash Streamlit
        (Session n'est pas hashable proprement).
    code_pilote : str
        Code 3-lettres (ex: "HAM", "VER") ou numéro.

    Retour
    ------
    tuple[fastf1.core.Lap, pd.DataFrame]
        Le tour le plus rapide et la télémétrie avec colonne `Distance`.

    Raises
    ------
    ValueError
        Si aucun tour valide n'est trouvé pour le pilote.
    """
    # Garantit que _car_data est en mémoire (sinon get_car_data crash)
    _ensure_session_loaded(_sess)

    laps = _sess.laps.pick_drivers(code_pilote)
    if laps is None or len(laps) == 0:
        raise ValueError(f"Aucun tour pour le pilote {code_pilote}")

    lap = _select_lap(laps, lap_number=None)
    if lap is None:
        raise ValueError(f"Aucun tour valide pour {code_pilote} (LapTime tous NaN ?)")

    tel = lap.get_car_data().add_distance()
    return lap, tel

def _round_upto(annee: int, upto_event: str) -> int | None:
    """Retourne le numéro de manche (1-based) correspondant à `upto_event`."""
    try:
        schedule = fastf1.get_event_schedule(annee, include_testing=False)
    except Exception as exc:
        logger.warning("get_event_schedule(%s) a échoué: %s", annee, exc)
        return None
    if 'EventName' not in schedule.columns:
        return None
    names = schedule['EventName'].tolist()
    if upto_event not in names:
        return None
    return names.index(upto_event) + 1


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

    # Fallback : boucler sur chaque course, mais en chargeant SEULEMENT les résultats
    try:
        schedule = fastf1.get_event_schedule(annee, include_testing=False)
    except Exception:
        return pd.DataFrame()
    chunks = []
    for i in range(rnd):
        ev = schedule.iloc[i]
        try:
            s = fastf1.get_session(annee, ev['EventName'], 'R')
            s.load(laps=False, telemetry=False, weather=False, messages=False)
            r = s.results
            if r is not None and not r.empty and 'BroadcastName' in r and 'Points' in r:
                chunks.append(r[['BroadcastName', 'Points', 'TeamName']].copy())
        except Exception as exc:
            logger.debug("Skip %s (%s)", ev.get('EventName'), exc)
            continue
    if not chunks:
        return pd.DataFrame()
    all_pts = pd.concat(chunks, ignore_index=True)
    classement = (all_pts.groupby(['BroadcastName', 'TeamName'], dropna=False)['Points']
                  .sum().reset_index())
    standings = classement.sort_values('Points', ascending=False).reset_index(drop=True)
    standings['Position'] = standings.index + 1
    return standings[['Position', 'BroadcastName', 'TeamName', 'Points']]


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

    try:
        schedule = fastf1.get_event_schedule(annee, include_testing=False)
    except Exception:
        return pd.DataFrame()
    chunks = []
    for i in range(rnd):
        ev = schedule.iloc[i]
        try:
            s = fastf1.get_session(annee, ev['EventName'], 'R')
            s.load(laps=False, telemetry=False, weather=False, messages=False)
            r = s.results
            if r is not None and not r.empty and 'TeamName' in r and 'Points' in r:
                chunks.append(r[['TeamName', 'Points']].copy())
        except Exception:
            continue
    if not chunks:
        return pd.DataFrame()
    all_pts = pd.concat(chunks, ignore_index=True)
    classement = (all_pts.groupby(['TeamName'], dropna=False)['Points']
                  .sum().reset_index())
    standings = classement.sort_values('Points', ascending=False).reset_index(drop=True)
    standings['Position'] = standings.index + 1
    return standings[['Position', 'TeamName', 'Points']]

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
def figure_positions_par_tour(sess, pilotes=None):
    """
    Crée et renvoie une figure Matplotlib qui trace la position de chaque pilote
    à la fin de chaque tour pour la session donnée.

    Paramètres
    ---------
    sess : fastf1.core.Session
        Session FastF1 déjà chargée (via `chargement_session`).
    pilotes : list[str] | None
        Liste optionnelle de codes pilotes (abréviations 3 lettres). Si None,
        tous les pilotes présents dans `sess.laps` sont tracés.

    Retour
    ------
    matplotlib.figure.Figure
    """
    # Validation entrée
    if sess is None or not hasattr(sess, "laps"):
        return _err_figure("Session invalide", figsize=(10, 5))

    laps = sess.laps
    if laps is None or len(laps) == 0:
        return _err_figure("Aucun tour dans cette session", figsize=(10, 5))

    if "Driver" not in laps.columns or "LapNumber" not in laps.columns or "Position" not in laps.columns:
        return _err_figure(
            "Colonnes manquantes (Driver/LapNumber/Position).\n"
            "Cette visualisation n'est disponible que pour les courses (R) avec données de classement par tour.",
            figsize=(10, 5),
        )

    # Mapping Abbreviation -> BroadcastName pour des légendes lisibles
    name_map = {}
    try:
        res = getattr(sess, "results", None)
        if res is not None and not res.empty and "Abbreviation" in res and "BroadcastName" in res:
            name_map = dict(zip(res["Abbreviation"], res["BroadcastName"]))
    except Exception:
        pass

    # Liste de pilotes : abréviations présentes dans les laps (fiable)
    if pilotes is None:
        pilotes = sorted(laps["Driver"].dropna().unique().tolist())

    if not pilotes:
        return _err_figure("Aucun pilote détecté dans les tours", figsize=(10, 5))

    # Figure (thème sombre)
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')
    ax.tick_params(colors="#e6edf3")
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")
    ax.xaxis.label.set_color("#e6edf3")
    ax.yaxis.label.set_color("#e6edf3")
    ax.title.set_color("#e6edf3")
    ax.grid(True, color="#21262d", linewidth=0.5, alpha=0.7)

    # Tentative d'utiliser la palette FastF1 (couleurs équipes). Si elle échoue,
    # fallback sur une cycle matplotlib + linestyle alterné — on ne saute PLUS
    # silencieusement le pilote.
    try:
        fastf1.plotting.setup_mpl(mpl_timedelta_support=False, color_scheme='fastf1')
    except Exception as exc:
        logger.warning("setup_mpl FastF1 a échoué: %s", exc)

    nb_tracé = 0
    for drv in pilotes:
        drv_laps = laps[laps["Driver"] == drv].sort_values("LapNumber")
        if drv_laps.empty:
            continue

        abb = drv_laps["Driver"].iloc[0]
        label = name_map.get(abb, abb)

        # Style FastF1 si possible, sinon défaut
        plot_kwargs = {"label": label, "linewidth": 1.6}
        try:
            style = fastf1.plotting.get_driver_style(
                identifier=abb, style=["color", "linestyle"], session=sess,
            )
            plot_kwargs.update(style)
        except Exception as exc:
            logger.debug("get_driver_style(%s) a échoué: %s", abb, exc)

        try:
            ax.plot(drv_laps["LapNumber"], drv_laps["Position"], **plot_kwargs)
            nb_tracé += 1
        except Exception as exc:
            logger.warning("plot(%s) a échoué: %s", abb, exc)

    if nb_tracé == 0:
        plt.close(fig)
        return _err_figure(
            "Aucune position n'a pu être tracée — vérifie que c'est bien une course (R).",
            figsize=(10, 5),
        )

    # Axes et légendes
    ax.set_ylim([20.5, 0.5])
    ax.set_yticks([1, 5, 10, 15, 20])
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
def figure_carte_vitesse(sess,
                         pilote,
                         lap_number: int | None = None,
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
    sess : fastf1.core.Session
        Session FastF1 déjà chargée.
    pilote : str | int
        Identifiant pilote (abréviation 3 lettres, numéro ou BroadcastName).
    lap_number : int | None
        Numéro de tour à tracer. Si None, utilise le tour le plus rapide.
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
    _ensure_session_loaded(sess)

    # Résoudre l'abréviation depuis BroadcastName/numéro si nécessaire
    drv_identifier = pilote
    try:
        res = getattr(sess, "results", None)
        if res is not None and not res.empty:
            if isinstance(pilote, str) and 'BroadcastName' in res.columns and 'Abbreviation' in res.columns:
                m = dict(zip(res['BroadcastName'], res['Abbreviation']))
                drv_identifier = m.get(pilote, pilote)
            if 'DriverNumber' in res.columns and 'Abbreviation' in res.columns:
                mnum = dict(zip(res['DriverNumber'].astype(str), res['Abbreviation']))
                drv_identifier = mnum.get(str(drv_identifier), drv_identifier)
    except Exception:
        pass

    # Récupérer le tour
    try:
        laps = sess.laps.pick_drivers(drv_identifier)
    except Exception as exc:
        logger.exception("pick_drivers(%s) a échoué", drv_identifier)
        return _err_figure(f"Pilote introuvable : {drv_identifier}\n{type(exc).__name__}: {exc}", figsize=figsize, dpi=dpi)

    if laps is None or len(laps) == 0:
        return _err_figure(f"Aucun tour pour le pilote {drv_identifier}", figsize=figsize, dpi=dpi)

    lap = _select_lap(laps, lap_number)
    if lap is None:
        return _err_figure(f"Tour indisponible pour {drv_identifier}", figsize=figsize, dpi=dpi)

    # Télémétrie
    try:
        tel = lap.get_telemetry()
    except Exception as exc:
        logger.exception("get_telemetry a échoué pour %s", drv_identifier)
        return _err_figure(f"Télémétrie indisponible : {type(exc).__name__}: {exc}", figsize=figsize, dpi=dpi)

    if tel is None or len(tel) == 0:
        return _err_figure(f"Télémétrie vide pour {drv_identifier}", figsize=figsize, dpi=dpi)

    if not all(c in tel.columns for c in ("X", "Y", "Speed")):
        return _err_figure("Colonnes X/Y/Speed manquantes dans la télémétrie", figsize=figsize, dpi=dpi)

    # Variables de tracé
    x = tel['X']
    y = tel['Y']
    speed = tel['Speed']

    # Segments colorés
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    fig, ax = plt.subplots(sharex=True, sharey=True, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    # Titre
    try:
        gp_name = sess.event.name
        year = int(sess.event.year)
    except Exception:
        gp_name, year = sess.name, ''
    title_id = drv_identifier
    try:
        # Utiliser BroadcastName si dispo pour le titre, sinon abréviation
        res = getattr(sess, "results", None)
        if res is not None and not res.empty and 'Abbreviation' in res and 'BroadcastName' in res:
            inv = dict(zip(res['Abbreviation'], res['BroadcastName']))
            title_id = inv.get(str(drv_identifier), str(drv_identifier))
    except Exception:
        pass
    fig.suptitle(f"{gp_name} {year} – {title_id} – Vitesse", size=18, y=0.97, color="#e6edf3")

    # Marges et axes
    plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.12)
    ax.axis('off')

    # Ligne de fond (piste) — gris foncé pour rester visible sur fond anthracite
    ax.plot(x, y, color='#30363d', linestyle='-', linewidth=linewidth_track, zorder=0)

    # Ligne colorée par la vitesse
    norm = plt.Normalize(speed.min(), speed.max())
    lc = LineCollection(segments, cmap=cmap, norm=norm, linestyle='-', linewidth=linewidth_speed)
    lc.set_array(speed)
    ax.add_collection(lc)

    # Ajustement des limites (LineCollection ne le fait pas seul)
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y.min(), y.max())
    ax.set_aspect('equal')

    # Barre de couleurs
    if show_colorbar:
        cbaxes = fig.add_axes([0.25, 0.05, 0.5, 0.04])
        normlegend = mpl.colors.Normalize(vmin=float(speed.min()), vmax=float(speed.max()))
        cb = mpl.colorbar.ColorbarBase(cbaxes, norm=normlegend, cmap=cmap, orientation="horizontal")
        cb.set_label("Vitesse (km/h)", color="#e6edf3")
        cb.ax.tick_params(colors="#e6edf3")
        cb.outline.set_edgecolor("#30363d")

    return fig


# --- Visualisation des rapports engagés (nGear) le long de la trajectoire ---
@_safe_figure
def figure_carte_rapports(sess,
                           pilote,
                           lap_number: int | None = None,
                           cmap=None,
                           figsize=(12, 6.75),
                           dpi=100,
                           linewidth_track: float = 16,
                           linewidth_gears: float = 4,
                           show_colorbar: bool = True):
    """
    Visualisation des rapports engagés (nGear) le long de la trajectoire.

    Paramètres
    ----------
    sess : fastf1.core.Session
        Session FastF1 déjà chargée.
    pilote : str | int
        Identifiant pilote (abréviation 3 lettres, numéro ou BroadcastName).
    lap_number : int | None
        Numéro de tour à tracer. Si None, utilise le tour le plus rapide.
    cmap : matplotlib colormap | None
        Colormap utilisée. Par défaut 'Paired'.
    figsize : tuple[float, float]
        Taille de la figure en pouces.
    dpi : int
        Résolution de la figure.
    linewidth_track : float
        Épaisseur de la ligne de fond (piste).
    linewidth_gears : float
        Épaisseur de la ligne colorée par le rapport engagé.
    show_colorbar : bool
        Afficher la barre de couleurs.

    Retour
    ------
    matplotlib.figure.Figure
    """
    _ensure_session_loaded(sess)

    # Choix de la colormap
    if cmap is None:
        cmap = mpl.colormaps['Paired']

    # Résoudre l'identifiant pilote (comme dans figure_carte_vitesse)
    drv_identifier = pilote
    try:
        res = getattr(sess, "results", None)
        if res is not None and not res.empty:
            if isinstance(pilote, str) and 'BroadcastName' in res.columns and 'Abbreviation' in res.columns:
                m = dict(zip(res['BroadcastName'], res['Abbreviation']))
                drv_identifier = m.get(pilote, pilote)
            if 'DriverNumber' in res.columns and 'Abbreviation' in res.columns:
                mnum = dict(zip(res['DriverNumber'].astype(str), res['Abbreviation']))
                drv_identifier = mnum.get(str(drv_identifier), drv_identifier)
    except Exception:
        pass

    # Sélection du tour
    try:
        laps = sess.laps.pick_drivers(drv_identifier)
    except Exception as exc:
        logger.exception("pick_drivers(%s) a échoué (rapports)", drv_identifier)
        return _err_figure(f"Pilote introuvable : {drv_identifier}\n{type(exc).__name__}: {exc}", figsize=figsize, dpi=dpi)

    if laps is None or len(laps) == 0:
        return _err_figure(f"Aucun tour pour le pilote {drv_identifier}", figsize=figsize, dpi=dpi)

    lap = _select_lap(laps, lap_number)
    if lap is None:
        return _err_figure(f"Tour indisponible pour {drv_identifier}", figsize=figsize, dpi=dpi)

    # Télémétrie
    try:
        tel = lap.get_telemetry()
    except Exception as exc:
        logger.exception("get_telemetry (rapports) a échoué pour %s", drv_identifier)
        return _err_figure(f"Télémétrie indisponible : {type(exc).__name__}: {exc}", figsize=figsize, dpi=dpi)

    if tel is None or len(tel) == 0:
        return _err_figure(f"Télémétrie vide pour {drv_identifier}", figsize=figsize, dpi=dpi)

    if not all(c in tel.columns for c in ("X", "Y", "nGear")):
        return _err_figure("Colonnes X/Y/nGear manquantes dans la télémétrie", figsize=figsize, dpi=dpi)

    x = np.array(tel['X'].values)
    y = np.array(tel['Y'].values)

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # nGear en float pour colormap et bornes 1..9 (boîtes 1..8 habituellement)
    gear = tel['nGear'].to_numpy().astype(float)

    # Figure
    fig, ax = plt.subplots(sharex=True, sharey=True, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    # Titre
    try:
        gp_name = sess.event.name
        year = int(sess.event.year)
    except Exception:
        gp_name, year = sess.name, ''
    title_id = drv_identifier
    try:
        res = getattr(sess, "results", None)
        if res is not None and not res.empty and 'Abbreviation' in res and 'BroadcastName' in res:
            inv = dict(zip(res['Abbreviation'], res['BroadcastName']))
            title_id = inv.get(str(drv_identifier), str(drv_identifier))
    except Exception:
        pass
    fig.suptitle(f"{gp_name} {year} – {title_id} – Rapports", size=18, y=0.97, color="#e6edf3")

    # Fond de piste — gris foncé pour rester visible sur fond anthracite
    ax.plot(x, y, color='#30363d', linestyle='-', linewidth=linewidth_track, zorder=0)

    # Collection de lignes colorées par rapport
    lc = LineCollection(segments, norm=plt.Normalize(1, cmap.N + 1), cmap=cmap)
    lc.set_array(gear)
    lc.set_linewidth(linewidth_gears)
    ax.add_collection(lc)

    # Aspect & axes — set_xlim/set_ylim avant axis('off')
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y.min(), y.max())
    ax.set_aspect('equal')
    ax.axis('off')

    # Colorbar (ticks centrés sur chaque couleur)
    if show_colorbar:
        cbar = plt.colorbar(mappable=lc, ax=ax, label="Rapport", boundaries=np.arange(1, 10), fraction=0.046, pad=0.04)
        cbar.set_ticks(np.arange(1.5, 9.5))
        cbar.set_ticklabels(np.arange(1, 9))
        cbar.set_label("Rapport", color="#e6edf3")
        cbar.ax.tick_params(colors="#e6edf3")
        cbar.outline.set_edgecolor("#30363d")

    return fig


# --- Carte du circuit avec numérotation des virages ---

@_safe_figure
def figure_carte_virages(sess,
                          pilote: str | int | None = None,
                          lap_number: int | None = None,
                          figsize=(12, 6.75),
                          dpi=100,
                          track_color='#e6edf3',
                          track_linewidth: float = 2.0,
                          bubble_color='#c1322d',
                          bubble_size: float = 160.0,
                          link_color='#484f58',
                          offset_length: float = 500.0,
                          show_title: bool = True):
    """
    Trace la carte du circuit à partir des données de position d'un tour et
    annote la carte avec les numéros de virage.

    Paramètres
    ----------
    sess : fastf1.core.Session
        Session FastF1 déjà chargée.
    pilote : str | int | None
        Pilote ciblé (abréviation / numéro / BroadcastName). Si None, on utilise
        simplement le tour le plus rapide de la session (tous pilotes).
    lap_number : int | None
        Numéro de tour à tracer. Si None, utilise le tour le plus rapide pour
        le pilote choisi (ou celui de la session si `pilote` est None).
    figsize, dpi :
        Taille et résolution de la figure.
    track_color, track_linewidth :
        Couleur/épaisseur de la ligne du tracé (piste).
    bubble_color, bubble_size :
        Couleur/taille des bulles contenant les numéros de virage.
    link_color :
        Couleur du trait joignant la piste à la bulle.
    offset_length :
        Longueur du vecteur de décalage latéral des étiquettes.
    show_title : bool
        Afficher le titre (localisation de l'événement).

    Retour
    ------
    matplotlib.figure.Figure
    """
    _ensure_session_loaded(sess)

    import numpy as _np

    def _rotate(xy, *, angle):
        rot_mat = _np.array([[ _np.cos(angle),  _np.sin(angle)],
                             [-_np.sin(angle),  _np.cos(angle)]])
        return _np.matmul(xy, rot_mat)

    # Sélection du tour
    laps = sess.laps
    if pilote is not None:
        # Tenter de résoudre l'identifiant abrégé comme dans les autres helpers
        drv_identifier = pilote
        try:
            res = getattr(sess, "results", None)
            if res is not None and not res.empty:
                if isinstance(pilote, str) and 'BroadcastName' in res.columns and 'Abbreviation' in res.columns:
                    m = dict(zip(res['BroadcastName'], res['Abbreviation']))
                    drv_identifier = m.get(pilote, pilote)
                if 'DriverNumber' in res.columns and 'Abbreviation' in res.columns:
                    mnum = dict(zip(res['DriverNumber'].astype(str), res['Abbreviation']))
                    drv_identifier = mnum.get(str(drv_identifier), drv_identifier)
        except Exception:
            pass
        laps = laps.pick_drivers(drv_identifier)

    if laps is None or len(laps) == 0:
        return _err_figure("Aucun tour disponible pour cette session", figsize=figsize, dpi=dpi)

    lap = _select_lap(laps, lap_number)
    if lap is None:
        return _err_figure("Tour indisponible (aucun tour valide trouvé)", figsize=figsize, dpi=dpi)

    # Position et infos circuit
    try:
        pos = lap.get_pos_data()
    except Exception as exc:
        logger.exception("get_pos_data a échoué")
        return _err_figure(f"Données de position indisponibles : {type(exc).__name__}: {exc}", figsize=figsize, dpi=dpi)

    try:
        circuit_info = sess.get_circuit_info()
    except Exception as exc:
        logger.warning("get_circuit_info a échoué: %s", exc)
        circuit_info = None

    if pos is None or len(pos) == 0:
        return _err_figure("Données de position vides", figsize=figsize, dpi=dpi)

    if not all(c in pos.columns for c in ("X", "Y")):
        return _err_figure("Colonnes X/Y manquantes dans les données de position", figsize=figsize, dpi=dpi)

    # Créer la figure (thème sombre)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    track = pos.loc[:, ('X', 'Y')].to_numpy()

    # Angle global de rotation de la carte
    track_angle = 0.0
    if circuit_info is not None and hasattr(circuit_info, 'rotation'):
        try:
            track_angle = float(circuit_info.rotation) / 180.0 * _np.pi
        except Exception:
            track_angle = 0.0

    rotated_track = _rotate(track, angle=track_angle)

    # Tracé piste
    ax.plot(rotated_track[:, 0], rotated_track[:, 1], color=track_color, linewidth=track_linewidth)

    # Annoter les virages
    if circuit_info is not None and getattr(circuit_info, 'corners', None) is not None and not circuit_info.corners.empty:
        offset_vec = _np.array([offset_length, 0])
        for _, corner in circuit_info.corners.iterrows():
            try:
                txt = f"{corner['Number']}{corner['Letter']}"

                # Angle local de la pancarte
                offset_angle = float(corner['Angle']) / 180.0 * _np.pi
                offset_x, offset_y = _rotate(offset_vec, angle=offset_angle)

                # Position texte
                text_x = float(corner['X']) + offset_x
                text_y = float(corner['Y']) + offset_y

                # Rotation globale pour rester cohérent avec la piste
                text_x, text_y = _rotate([text_x, text_y], angle=track_angle)
                track_x, track_y = _rotate([float(corner['X']), float(corner['Y'])], angle=track_angle)

                # Bulle + lien
                ax.scatter(text_x, text_y, color=bubble_color, s=bubble_size, zorder=3)
                ax.plot([track_x, text_x], [track_y, text_y], color=link_color, linewidth=1, zorder=2)
                ax.text(text_x, text_y, txt, va='center_baseline', ha='center',
                        size='small', color='#ffffff', fontweight='bold', zorder=4)
            except Exception:
                continue

    # Finition
    if show_title:
        try:
            title_txt = sess.event['Location'] if isinstance(sess.event, dict) else getattr(sess.event, 'Location', None)
            if not title_txt:
                title_txt = getattr(sess.event, 'name', '')
            plt.title(title_txt, color="#e6edf3", fontsize=16, fontweight=500, pad=12)
        except Exception:
            pass

    # Limites avant axis('off')
    ax.set_xlim(rotated_track[:, 0].min(), rotated_track[:, 0].max())
    ax.set_ylim(rotated_track[:, 1].min(), rotated_track[:, 1].max())
    ax.set_aspect('equal')
    ax.axis('off')
    return fig

