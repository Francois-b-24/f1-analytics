import pandas as pd
import numpy as np

def formatage_timedelta(td) -> str:
    """Formate un pandas.Timedelta ou None en mm:ss.ms."""
    if pd.isna(td):
        return "—"
    total_ms = int(td.total_seconds() * 1000)
    minutes, ms_rem = divmod(total_ms, 60_000)
    seconds, ms = divmod(ms_rem, 1000)
    return f"{minutes:02d}:{seconds:02d}.{ms:03d}"

def secs(td) -> float:
    """Convertit Timedelta en secondes (float)."""
    if pd.isna(td):
        return np.nan
    return td.total_seconds()