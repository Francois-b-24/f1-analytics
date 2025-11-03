import pandas as pd
import streamlit as st
import fastf1
from .utils import secs, formatage_timedelta

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
            if not r.empty and 'Abbreviation' in r and 'Points' in r:
                chunks.append(r[['Abbreviation', 'Points', 'TeamName']])
        except Exception:
            continue

    if not chunks:
        return pd.DataFrame()

    all_pts = pd.concat(chunks, ignore_index=True)
    classement = (all_pts.groupby(['Abbreviation', 'TeamName'], dropna=False)['Points']
                        .sum().reset_index())
    standings = classement.sort_values('Points', ascending=False).reset_index(drop=True)
    standings['Position'] = standings.index + 1
    return standings[['Position', 'Abbreviation', 'TeamName', 'Points']]

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
        cols = [c for c in ["Position","Abbreviation","DriverNumber","TeamName","TeamColor","Points","Status","Time","FastestLapTime"] if c in results_df.columns]
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