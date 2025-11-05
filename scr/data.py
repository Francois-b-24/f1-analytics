from __future__ import annotations

import pandas as pd
import streamlit as st
import fastf1
from .utils import secs, formatage_timedelta
import matplotlib.pyplot as plt
import fastf1.plotting
import numpy as np
import matplotlib as mpl
from matplotlib.collections import LineCollection

@st.cache_data(show_spinner=False)
def chargement_session(annee: int, course: str, sess_type: str):
    """ Fonction permettant de charger une session (week-end de GP)"""
    sess = fastf1.get_session(annee, course, sess_type)
    sess.load()

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
    except Exception:
        meteo = pd.DataFrame()

    try:
        results = sess.results.copy().reset_index(drop=True)
    except Exception:
        results = pd.DataFrame()

    return dict(
        session = sess,
        nom=sess.name,
        tours=tours,
        pilotes=driver_codes,
        meteo=meteo,
        resultats=results,
    )

@st.cache_data(show_spinner=False)
def tour_rapide_tel(session_key: str, _tours_df: pd.DataFrame, code_pilote: str):
    """Fonction pour obtenir les informations sur le tour le plus rapide pour un pilote donné"""
    tours_df = _tours_df.pick_driver(code_pilote)
    plus_rapide = tours_df.pick_fastest()
    tel = plus_rapide.get_car_data().add_distance()
    return plus_rapide, tel

@st.cache_data(show_spinner=True)
def calcul_classement_pilote(annee: int, upto_event: str) -> pd.DataFrame:
    try:
        schedule = fastf1.get_event_schedule(annee, include_testing=False)
    except Exception:
        return pd.DataFrame()
    if 'EventName' not in schedule:
        return pd.DataFrame()
    nom = schedule['EventName'].tolist()
    if upto_event not in nom:
        return pd.DataFrame()

    upto_idx = nom.index(upto_event)
    chunks = []
    for i in range(upto_idx + 1):
        ev = schedule.iloc[i]
        try:
            s = fastf1.get_session(annee, ev['EventName'], 'R')
            s.load()
            r = s.results.copy()
            if not r.empty and 'BroadcastName' in r and 'Points' in r:
                chunks.append(r[['BroadcastName', 'Points', 'TeamName']])
        except Exception:
            continue

    if not chunks:
        return pd.DataFrame()

    all_pts = pd.concat(chunks, ignore_index=True)
    classement = (all_pts.groupby(['BroadcastName', 'TeamName'], dropna=False)['Points']
                        .sum().reset_index())
    standings = classement.sort_values('Points', ascending=False).reset_index(drop=True)
    standings['Position'] = standings.index + 1
    return standings[['Position', 'BroadcastName', 'TeamName', 'Points']]

@st.cache_data(show_spinner=True)
def calcul_classement_constructeur(annee: int, upto_event: str) -> pd.DataFrame:
    try:
        schedule = fastf1.get_event_schedule(annee, include_testing=False)
    except Exception:
        return pd.DataFrame()
    if 'EventName' not in schedule:
        return pd.DataFrame()
    noms = schedule['EventName'].tolist()
    if upto_event not in noms:
        return pd.DataFrame()

    upto_idx = noms.index(upto_event)
    chunks = []
    for i in range(upto_idx + 1):
        ev = schedule.iloc[i]
        try:
            s = fastf1.get_session(annee, ev['EventName'], 'R')
            s.load()
            r = s.results.copy()
            if not r.empty and 'TeamName' in r and 'Points' in r:
                chunks.append(r[['TeamName','Points']])
        except Exception:
            continue

    if not chunks:
        return pd.DataFrame()

    all_pts = pd.concat(chunks, ignore_index=True)
    classement = (all_pts.groupby(['TeamName'], dropna=False)['Points']
                        .sum().reset_index())
    standings = classement.sort_values('Points', ascending=False).reset_index(drop=True)
    standings['Position'] = standings.index + 1
    return standings[['Position','TeamName','Points']]

def classement_session(nb_tours: pd.DataFrame, results_df: pd.DataFrame, sess_type: str) -> pd.DataFrame:
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



def figure_positions_par_tour(sess, pilotes=None):
    """
    Crée et renvoie une figure Matplotlib qui trace la position de chaque pilote
    à la fin de chaque tour pour la session donnée.

    Paramètres
    ---------
    sess : fastf1.core.Session
        Session FastF1 déjà chargée (via `chargement_session`).
    pilotes : list[str] | None
        Liste optionnelle de codes pilotes (abréviations 3 lettres) ou numéros.
        Si None, tous les pilotes présents dans la session sont tracés.

    Retour
    ------
    matplotlib.figure.Figure
        Figure prête à être affichée dans Streamlit avec `st.pyplot(fig)`.
    """
    # Palette de couleurs FastF1 (désactive le support timedelta car non nécessaire ici)
    fastf1.plotting.setup_mpl(mpl_timedelta_support=False, color_scheme='fastf1')

    # Mapping Abbreviation -> BroadcastName pour des légendes lisibles
    name_map = {}
    try:
        res = getattr(sess, "results", None)
        if res is not None and not res.empty and "Abbreviation" in res and "BroadcastName" in res:
            name_map = dict(zip(res["Abbreviation"], res["BroadcastName"]))
    except Exception:
        pass

    # Détermine la liste des pilotes à tracer
    try:
        if pilotes is None:
            pilotes = list(sess.drivers)  # numéros
        # `pick_drivers` accepte numéros ou abréviations
    except Exception:
        # fallback : déduire depuis le DataFrame des tours
        try:
            pilotes = sorted(sess.laps["Driver"].dropna().unique().tolist())
        except Exception:
            pilotes = []

    fig, ax = plt.subplots(figsize=(8.0, 4.9))
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')

    for drv in pilotes:
        try:
            drv_laps = sess.laps.pick_drivers(drv)
            if drv_laps is None or drv_laps.empty:
                continue

            # Identifiant style basé sur l'abréviation (colonne 'Driver') du premier tour
            abb = drv_laps["Driver"].iloc[0]
            style = fastf1.plotting.get_driver_style(
                identifier=abb,
                style=["color", "linestyle"],
                session=sess,
            )
            label = name_map.get(abb, abb)

            ax.plot(drv_laps["LapNumber"], drv_laps["Position"], label=label, **style)
        except Exception:
            continue

    # Axes et légendes
    ax.set_ylim([20.5, 0.5])
    ax.set_yticks([1, 5, 10, 15, 20])
    ax.set_xlabel("Tour")
    ax.set_ylabel("Position")
    ax.legend(bbox_to_anchor=(1.0, 1.02), title="Pilotes")
    plt.tight_layout()

    return fig


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
    laps = sess.laps.pick_drivers(drv_identifier)
    if laps is None or laps.empty:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')
        ax.text(0.5, 0.5, "Aucun tour pour ce pilote", ha='center', va='center')
        ax.axis('off')
        return fig

    if lap_number is not None:
        lap = laps.loc[laps['LapNumber'] == lap_number]
        if lap is None or lap.empty:
            # fallback sur le plus rapide
            lap = laps.pick_fastest()
        else:
            # lap est un DataFrame d'une seule ligne -> convertir en Lap object
            lap = lap.iloc[0]
    else:
        lap = laps.pick_fastest()

    # Télémetrie avec position XY et vitesse (peut être get_telemetry selon version FastF1)
    try:
        tel = lap.get_telemetry()
    except Exception:
        # compatibilité avec anciens attributs
        tel = getattr(lap, 'telemetry', None)
        if tel is None:
            fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
            fig.patch.set_facecolor('white')
            ax.set_facecolor('white')
            ax.text(0.5, 0.5, "Télémetrie indisponible", ha='center', va='center')
            ax.axis('off')
            return fig

    # Variables de tracé
    x = tel['X']
    y = tel['Y']
    speed = tel['Speed']

    # Segments colorés
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    fig, ax = plt.subplots(sharex=True, sharey=True, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')

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
    fig.suptitle(f"{gp_name} {year} – {title_id} – Vitesse", size=18, y=0.97)

    # Marges et axes
    plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.12)
    ax.axis('off')

    # Ligne de fond (piste)
    ax.plot(x, y, color='black', linestyle='-', linewidth=linewidth_track, zorder=0)

    # Ligne colorée par la vitesse
    norm = plt.Normalize(speed.min(), speed.max())
    lc = LineCollection(segments, cmap=cmap, norm=norm, linestyle='-', linewidth=linewidth_speed)
    lc.set_array(speed)
    ax.add_collection(lc)

    # Barre de couleurs
    if show_colorbar:
        cbaxes = fig.add_axes([0.25, 0.05, 0.5, 0.05])
        normlegend = mpl.colors.Normalize(vmin=float(speed.min()), vmax=float(speed.max()))
        mpl.colorbar.ColorbarBase(cbaxes, norm=normlegend, cmap=cmap, orientation="horizontal")

    plt.tight_layout()
    return fig


# --- Visualisation des rapports engagés (nGear) le long de la trajectoire ---
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
    laps = sess.laps.pick_drivers(drv_identifier)
    if laps is None or laps.empty:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')
        ax.text(0.5, 0.5, "Aucun tour pour ce pilote", ha='center', va='center')
        ax.axis('off')
        return fig

    if lap_number is not None:
        lap = laps.loc[laps['LapNumber'] == lap_number]
        if lap is None or lap.empty:
            lap = laps.pick_fastest()
        else:
            lap = lap.iloc[0]
    else:
        lap = laps.pick_fastest()

    # Télémetrie et données
    try:
        tel = lap.get_telemetry()
    except Exception:
        tel = getattr(lap, 'telemetry', None)
        if tel is None:
            fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
            fig.patch.set_facecolor('white')
            ax.set_facecolor('white')
            ax.text(0.5, 0.5, "Télémetrie indisponible", ha='center', va='center')
            ax.axis('off')
            return fig

    x = np.array(tel['X'].values)
    y = np.array(tel['Y'].values)

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # nGear en float pour colormap et bornes 1..9 (boîtes 1..8 habituellement)
    gear = tel['nGear'].to_numpy().astype(float)

    # Figure
    fig, ax = plt.subplots(sharex=True, sharey=True, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')

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
    fig.suptitle(f"{gp_name} {year} – {title_id} – Rapports", size=18, y=0.97)

    # Fond de piste
    ax.plot(x, y, color='black', linestyle='-', linewidth=linewidth_track, zorder=0)

    # Collection de lignes colorées par rapport
    lc = LineCollection(segments, norm=plt.Normalize(1, cmap.N + 1), cmap=cmap)
    lc.set_array(gear)
    lc.set_linewidth(linewidth_gears)
    ax.add_collection(lc)

    # Aspect & axes
    ax.axis('equal')
    ax.tick_params(labelleft=False, left=False, labelbottom=False, bottom=False)
    ax.axis('off')

    # Colorbar (ticks centrés sur chaque couleur)
    if show_colorbar:
        cbar = plt.colorbar(mappable=lc, ax=ax, label="Rapport", boundaries=np.arange(1, 10), fraction=0.046, pad=0.04)
        cbar.set_ticks(np.arange(1.5, 9.5))
        cbar.set_ticklabels(np.arange(1, 9))

    plt.tight_layout()
    return fig


# --- Carte du circuit avec numérotation des virages ---

def figure_carte_virages(sess,
                          pilote: str | int | None = None,
                          lap_number: int | None = None,
                          figsize=(12, 6.75),
                          dpi=100,
                          track_color='black',
                          track_linewidth: float = 2.0,
                          bubble_color='grey',
                          bubble_size: float = 140.0,
                          link_color='grey',
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

    if laps is None or laps.empty:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')
        ax.text(0.5, 0.5, "Aucun tour disponible", ha='center', va='center')
        ax.axis('off')
        return fig

    if lap_number is not None:
        lap = laps.loc[laps['LapNumber'] == lap_number]
        if lap is None or lap.empty:
            lap = laps.pick_fastest()
        else:
            lap = lap.iloc[0]
    else:
        lap = laps.pick_fastest()

    # Position et infos circuit
    try:
        pos = lap.get_pos_data()
    except Exception:
        pos = None
    try:
        circuit_info = sess.get_circuit_info()
    except Exception:
        circuit_info = None

    # Créer la figure
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    if pos is None or pos.empty:
        ax.text(0.5, 0.5, "Données de position indisponibles", ha='center', va='center')
        ax.axis('off')
        return fig

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
                ax.scatter(text_x, text_y, color=bubble_color, s=bubble_size)
                ax.plot([track_x, text_x], [track_y, text_y], color=link_color)
                ax.text(text_x, text_y, txt, va='center_baseline', ha='center', size='small', color='white')
            except Exception:
                continue

    # Finition
    if show_title:
        try:
            title_txt = sess.event['Location'] if isinstance(sess.event, dict) else getattr(sess.event, 'Location', None)
            if not title_txt:
                title_txt = getattr(sess.event, 'name', '')
            plt.title(title_txt)
        except Exception:
            pass
    plt.xticks([])
    plt.yticks([])
    plt.axis('equal')
    plt.tight_layout()
    return fig

