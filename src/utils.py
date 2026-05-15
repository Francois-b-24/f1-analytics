import pandas as pd
import numpy as np

def formatage_timedelta(td) -> str:
    """
    Formate un pandas.Timedelta ou None en format mm:ss.ms.
    
    Paramètres
    ----------
    td : pandas.Timedelta ou None
        L'intervalle de temps à formater.
    
    Retour
    ------
    str
        Le temps formaté au format mm:ss.ms ou "—" si None/NaN.
    """
    if pd.isna(td):
        return "—"
    total_ms = int(td.total_seconds() * 1000)
    minutes, ms_rem = divmod(total_ms, 60_000)
    seconds, ms = divmod(ms_rem, 1000)
    return f"{minutes:02d}:{seconds:02d}.{ms:03d}"

def secs(td) -> float:
    """
    Convertit un pandas.Timedelta en secondes (float).
    
    Paramètres
    ----------
    td : pandas.Timedelta ou None
        L'intervalle de temps à convertir.
    
    Retour
    ------
    float
        Le nombre de secondes (float) ou np.nan si None/NaN.
    """
    if pd.isna(td):
        return np.nan
    return td.total_seconds()