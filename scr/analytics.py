"""
Calculs analytiques avancés pour l'application F1 Analytics.

Regroupe les features :
- Analyse par secteur (F1)
- Dégradation de stint (F2)
- Delta time overlay entre deux pilotes (F3)
- Heatmap de dégradation pneus (F4)

Toutes les fonctions consomment le DataFrame `tours` renvoyé par
`scr.data.chargement_session` (déjà enrichi de colonnes LapSeconds et
Sector[1-3]TimeSec).
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("f1_analytics.analytics")


# ---------------------------------------------------------------------------
# F1 — Analyse par secteur
# ---------------------------------------------------------------------------
def sector_times_long(tours: pd.DataFrame, drivers: list[str] | None = None) -> pd.DataFrame:
    """
    Retourne un DataFrame long pour les temps par secteur.

    Colonnes: Driver, LapNumber, Sector (S1/S2/S3), Seconds.
    Ne garde que les lignes valides (non NaN, > 0).
    """
    needed = {"Driver", "LapNumber", "Sector1TimeSec", "Sector2TimeSec", "Sector3TimeSec"}
    if not needed.issubset(tours.columns):
        return pd.DataFrame(columns=["Driver", "LapNumber", "Sector", "Seconds"])

    df = tours.copy()
    if drivers:
        df = df[df["Driver"].isin(drivers)]
    if df.empty:
        return pd.DataFrame(columns=["Driver", "LapNumber", "Sector", "Seconds"])

    frames = []
    for i, col in enumerate(["Sector1TimeSec", "Sector2TimeSec", "Sector3TimeSec"], start=1):
        sub = df[["Driver", "LapNumber", col]].rename(columns={col: "Seconds"})
        sub["Sector"] = f"S{i}"
        frames.append(sub)
    long = pd.concat(frames, ignore_index=True)
    long = long.dropna(subset=["Seconds"])
    long = long[long["Seconds"] > 0]
    return long[["Driver", "LapNumber", "Sector", "Seconds"]]


def sector_best_per_driver(tours: pd.DataFrame) -> pd.DataFrame:
    """
    Meilleur temps par secteur pour chaque pilote + delta au meilleur global.

    Retourne colonnes: Driver, S1, S2, S3, Total, DeltaS1, DeltaS2, DeltaS3, DeltaTotal.
    """
    long = sector_times_long(tours)
    if long.empty:
        return pd.DataFrame()

    best = (
        long.groupby(["Driver", "Sector"])["Seconds"]
        .min()
        .unstack("Sector")
        .reset_index()
    )
    for c in ("S1", "S2", "S3"):
        if c not in best.columns:
            best[c] = np.nan
    best["Total"] = best[["S1", "S2", "S3"]].sum(axis=1, min_count=3)

    for c in ("S1", "S2", "S3", "Total"):
        ref = best[c].min(skipna=True)
        best[f"Delta{c}"] = best[c] - ref

    return best.sort_values("Total").reset_index(drop=True)


# ---------------------------------------------------------------------------
# F2 — Dégradation de stint
# ---------------------------------------------------------------------------
def stint_degradation(
    tours: pd.DataFrame,
    drivers: list[str] | None = None,
    min_laps: int = 4,
    clip_outliers_iqr: float = 1.5,
) -> pd.DataFrame:
    """
    Calcule l'âge de pneu (TyreLife) par stint et filtre les tours invalides.

    - Retire les tours avec PitInTime/PitOutTime non-null (in/out lap).
    - Retire les outliers au sens IQR × `clip_outliers_iqr` **par stint**.
    - Ne garde que les stints ≥ `min_laps` tours valides.

    Colonnes retournées: Driver, Stint, Compound, TyreLife, LapNumber, LapSeconds.
    """
    required = {"Driver", "Stint", "Compound", "LapNumber", "LapSeconds"}
    if not required.issubset(tours.columns):
        return pd.DataFrame(columns=list(required) + ["TyreLife"])

    df = tours.copy()
    if drivers:
        df = df[df["Driver"].isin(drivers)]
    df = df.dropna(subset=["Stint", "Compound", "LapSeconds"])
    if df.empty:
        return pd.DataFrame(columns=list(required) + ["TyreLife"])

    # Retire in/out laps
    for col in ("PitInTime", "PitOutTime"):
        if col in df.columns:
            df = df[df[col].isna()]

    # TyreLife: FastF1 fournit déjà la colonne, sinon calcul
    if "TyreLife" not in df.columns or df["TyreLife"].isna().all():
        df = df.sort_values(["Driver", "Stint", "LapNumber"])
        df["TyreLife"] = df.groupby(["Driver", "Stint"]).cumcount() + 1

    # Outliers par stint (IQR) — via masque vectorisé pour éviter apply()
    grp = df.groupby(["Driver", "Stint"])["LapSeconds"]
    q1 = grp.transform(lambda s: s.quantile(0.25))
    q3 = grp.transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    lo = q1 - clip_outliers_iqr * iqr
    hi = q3 + clip_outliers_iqr * iqr
    df = df[(df["LapSeconds"] >= lo) & (df["LapSeconds"] <= hi)]

    # Filtre stints courts
    counts = df.groupby(["Driver", "Stint"])["LapNumber"].transform("count")
    df = df[counts >= min_laps]

    return df[["Driver", "Stint", "Compound", "TyreLife", "LapNumber", "LapSeconds"]].reset_index(drop=True)


def stint_degradation_fits(deg_df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajuste une régression linéaire LapSeconds ~ TyreLife sur chaque (Driver, Stint).

    Retourne: Driver, Stint, Compound, Laps, Slope (s/tour), Intercept, R2.
    Slope = taux de dégradation estimé en secondes par tour.
    """
    if deg_df.empty:
        return pd.DataFrame(columns=["Driver", "Stint", "Compound", "Laps", "Slope", "Intercept", "R2"])

    rows = []
    for (drv, stint), g in deg_df.groupby(["Driver", "Stint"]):
        if len(g) < 3:
            continue
        x = g["TyreLife"].to_numpy(dtype=float)
        y = g["LapSeconds"].to_numpy(dtype=float)
        try:
            slope, intercept = np.polyfit(x, y, 1)
            y_pred = slope * x + intercept
            ss_res = float(np.sum((y - y_pred) ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
        except Exception as exc:
            logger.debug("polyfit failed on (%s, %s): %s", drv, stint, exc)
            continue
        rows.append(
            {
                "Driver": drv,
                "Stint": int(stint),
                "Compound": g["Compound"].iloc[0],
                "Laps": int(len(g)),
                "Slope": float(slope),
                "Intercept": float(intercept),
                "R2": float(r2) if not np.isnan(r2) else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["Driver", "Stint"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# F3 — Delta time overlay entre 2 pilotes
# ---------------------------------------------------------------------------
def delta_time_vs_distance(tel_ref: pd.DataFrame, tel_cmp: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule l'écart de temps cumulé entre deux télémétries alignées sur la distance.

    Approche : intégrale de 1/Speed le long de la distance pour chaque pilote,
    puis interpolation sur une grille commune. Delta > 0 = `tel_cmp` est en retard.

    Paramètres
    ----------
    tel_ref, tel_cmp : DataFrame
        Doivent contenir les colonnes 'Distance' (m) et 'Speed' (km/h).

    Retour
    ------
    DataFrame avec colonnes Distance, TimeRef, TimeCmp, Delta (secondes).
    """
    if tel_ref is None or tel_cmp is None:
        return pd.DataFrame(columns=["Distance", "TimeRef", "TimeCmp", "Delta"])
    if not {"Distance", "Speed"}.issubset(tel_ref.columns) or not {"Distance", "Speed"}.issubset(tel_cmp.columns):
        return pd.DataFrame(columns=["Distance", "TimeRef", "TimeCmp", "Delta"])

    def _cum_time(tel: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        d = tel["Distance"].to_numpy(dtype=float)
        v = tel["Speed"].to_numpy(dtype=float) / 3.6  # km/h → m/s
        # Évite divisions par zéro
        v = np.where(v < 1.0, 1.0, v)
        # Ordre croissant de distance
        order = np.argsort(d)
        d, v = d[order], v[order]
        # Supprime doublons de distance
        uniq = np.concatenate([[True], np.diff(d) > 1e-6])
        d, v = d[uniq], v[uniq]
        # t(i) = t(i-1) + (d(i)-d(i-1)) / ((v(i)+v(i-1))/2)
        dt = np.zeros_like(d)
        if len(d) > 1:
            v_mean = (v[1:] + v[:-1]) / 2.0
            dt[1:] = np.diff(d) / v_mean
        return d, np.cumsum(dt)

    d_ref, t_ref = _cum_time(tel_ref)
    d_cmp, t_cmp = _cum_time(tel_cmp)
    if len(d_ref) < 2 or len(d_cmp) < 2:
        return pd.DataFrame(columns=["Distance", "TimeRef", "TimeCmp", "Delta"])

    d_min = max(d_ref.min(), d_cmp.min())
    d_max = min(d_ref.max(), d_cmp.max())
    if d_max <= d_min:
        return pd.DataFrame(columns=["Distance", "TimeRef", "TimeCmp", "Delta"])

    grid = np.linspace(d_min, d_max, 500)
    t_ref_i = np.interp(grid, d_ref, t_ref)
    t_cmp_i = np.interp(grid, d_cmp, t_cmp)
    # Recaler pour que delta(0) = 0
    t_ref_i -= t_ref_i[0]
    t_cmp_i -= t_cmp_i[0]
    return pd.DataFrame(
        {
            "Distance": grid,
            "TimeRef": t_ref_i,
            "TimeCmp": t_cmp_i,
            "Delta": t_cmp_i - t_ref_i,
        }
    )


# ---------------------------------------------------------------------------
# F4 — Heatmap de dégradation pneus
# ---------------------------------------------------------------------------
def tyre_degradation_matrix(
    tours: pd.DataFrame,
    drivers: list[str] | None = None,
) -> pd.DataFrame:
    """
    Construit une matrice (Driver × LapNumber) → LapSeconds, ré-exprimée
    comme delta (en secondes) par rapport au meilleur tour personnel du pilote.

    Cela normalise par base de vitesse et rend visible la dégradation /
    les pit-in / les pneus neufs sur un fond commun.
    """
    required = {"Driver", "LapNumber", "LapSeconds"}
    if not required.issubset(tours.columns):
        return pd.DataFrame()

    df = tours.dropna(subset=["LapSeconds"])
    if drivers:
        df = df[df["Driver"].isin(drivers)]
    if df.empty:
        return pd.DataFrame()

    # Retire in/out laps pour un delta propre
    for col in ("PitInTime", "PitOutTime"):
        if col in df.columns:
            df = df[df[col].isna()]

    best = df.groupby("Driver")["LapSeconds"].transform("min")
    df = df.assign(DeltaToPB=df["LapSeconds"] - best)

    mat = (
        df.pivot_table(
            index="Driver",
            columns="LapNumber",
            values="DeltaToPB",
            aggfunc="first",
        )
        .sort_index()
    )
    return mat
