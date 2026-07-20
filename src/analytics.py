"""
Calculs analytiques avancés pour l'application F1 Analytics.

Regroupe les features :
- Analyse par secteur (F1)
- Dégradation de stint (F2)
- Delta time overlay entre deux pilotes (F3)
- Heatmap de dégradation pneus (F4)
- Proxys d'énergie 2026 (F5)

Les fonctions F1-F4 consomment le DataFrame `tours` renvoyé par
`src.data.chargement_session` (déjà enrichi de colonnes LapSeconds et
Sector[1-3]TimeSec). Les fonctions F5 consomment les DataFrames de
télémétrie de `tel_par_pilote` (Distance, Speed, Throttle, Brake).
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


# ---------------------------------------------------------------------------
# F5 — Proxys d'énergie 2026
# ---------------------------------------------------------------------------
# AVERTISSEMENT IMPORTANT
# La F1 ne publie AUCUNE donnée d'énergie : état de charge ERS, taux de
# déploiement/récupération MGU-K, mode d'aéro active. Confirmé par le mainteneur
# de FastF1 (discussion #861) : « F1 has decided to not make any data on active
# aero and ERS state available publicly ».
#
# Les fonctions ci-dessous ne mesurent donc rien : elles DÉRIVENT des indicateurs
# de comportement à partir des seuls canaux réellement publiés (Speed, Throttle,
# Brake). Ce sont des estimations sans vérité terrain, à présenter comme telles.
#
# Le canal DRS est volontairement ignoré : vérifié sur les données réelles, il ne
# contient que des 0 en 2026 comme en 2024, donc inexploitable.
# ---------------------------------------------------------------------------

# Seuils réglementaires 2026 : le déploiement MGU-K décroît à partir de 290 km/h
# et s'annule à 355 km/h.
DEPLOY_TAPER_START_KMH = 290.0
DEPLOY_TAPER_END_KMH = 355.0


def _segments_from_mask(mask: pd.Series) -> list[tuple[int, int]]:
    """Retourne les segments contigus [(i_debut, i_fin_inclus), ...] où mask est vrai.

    Utilitaire interne partagé par les détections de phases (freinage, traction).
    """
    if mask is None or len(mask) == 0:
        return []
    values = mask.fillna(False).to_numpy(dtype=bool)
    if not values.any():
        return []

    segments: list[tuple[int, int]] = []
    start: int | None = None
    for i, active in enumerate(values):
        if active and start is None:
            start = i
        elif not active and start is not None:
            segments.append((start, i - 1))
            start = None
    if start is not None:
        segments.append((start, len(values) - 1))
    return segments


def phases_telemetrie(
    tel: pd.DataFrame,
    seuil_throttle: float = 90.0,
    distance_min_m: float = 20.0,
) -> pd.DataFrame:
    """Découpe un tour en phases de freinage et de pleine traction.

    Proxy des fenêtres de récupération (freinage) et de déploiement (traction).
    Ce n'est PAS une mesure d'énergie — voir l'avertissement du module.

    Paramètres
    ----------
    tel : DataFrame
        Télémétrie d'un tour, colonnes Distance, Speed, Throttle, Brake.
    seuil_throttle : float
        Seuil (%) au-delà duquel on considère la traction comme pleine.
    distance_min_m : float
        Longueur minimale d'un segment pour être retenu (filtre le bruit).

    Retour
    ------
    DataFrame : Phase ("Freinage"/"Traction"), DistanceDebut, DistanceFin,
    Longueur (m), VitesseEntree, VitesseSortie.
    """
    cols = {"Distance", "Speed"}
    if tel is None or tel.empty or not cols.issubset(tel.columns):
        return pd.DataFrame(
            columns=["Phase", "DistanceDebut", "DistanceFin", "Longueur",
                     "VitesseEntree", "VitesseSortie"]
        )

    df = tel.sort_values("Distance").reset_index(drop=True)

    masques: dict[str, pd.Series] = {}
    if "Brake" in df.columns:
        masques["Freinage"] = df["Brake"].astype(bool)
    if "Throttle" in df.columns:
        masques["Traction"] = df["Throttle"] >= seuil_throttle

    rows = []
    for phase, mask in masques.items():
        for i0, i1 in _segments_from_mask(mask):
            d0 = float(df["Distance"].iloc[i0])
            d1 = float(df["Distance"].iloc[i1])
            longueur = d1 - d0
            if longueur < distance_min_m:
                continue
            rows.append({
                "Phase": phase,
                "DistanceDebut": d0,
                "DistanceFin": d1,
                "Longueur": longueur,
                "VitesseEntree": float(df["Speed"].iloc[i0]),
                "VitesseSortie": float(df["Speed"].iloc[i1]),
            })

    if not rows:
        return pd.DataFrame(
            columns=["Phase", "DistanceDebut", "DistanceFin", "Longueur",
                     "VitesseEntree", "VitesseSortie"]
        )
    return pd.DataFrame(rows).sort_values("DistanceDebut").reset_index(drop=True)


def resume_proxys_energie(tel: pd.DataFrame, seuil_throttle: float = 90.0) -> dict:
    """Agrège des indicateurs de comportement énergétique sur un tour.

    Toutes les valeurs sont des ESTIMATIONS dérivées de Speed/Throttle/Brake.

    Retour
    ------
    dict : longueur du tour, part et distance de freinage (proxy récupération),
    part et distance de pleine traction (proxy déploiement), distance passée
    au-delà du seuil de décroissance MGU-K (290 km/h), vitesse maximale,
    nombre de zones de freinage.
    """
    vide = {
        "distance_tour": 0.0,
        "part_freinage": 0.0, "distance_freinage": 0.0, "nb_freinages": 0,
        "part_traction": 0.0, "distance_traction": 0.0,
        "distance_au_dela_taper": 0.0, "part_au_dela_taper": 0.0,
        "vitesse_max": 0.0,
    }
    if tel is None or tel.empty or "Distance" not in tel.columns or "Speed" not in tel.columns:
        return vide

    df = tel.sort_values("Distance").reset_index(drop=True)
    d = df["Distance"].to_numpy(dtype=float)
    if len(d) < 2:
        return vide

    # Longueur représentée par chaque échantillon (différentielle avant).
    pas = np.diff(d, append=d[-1])
    pas = np.clip(pas, 0.0, None)
    total = float(pas.sum())
    if total <= 0:
        return vide

    res = dict(vide)
    res["distance_tour"] = total
    res["vitesse_max"] = float(df["Speed"].max())

    if "Brake" in df.columns:
        m = df["Brake"].fillna(False).to_numpy(dtype=bool)
        dist = float(pas[m].sum())
        res["distance_freinage"] = dist
        res["part_freinage"] = dist / total
        res["nb_freinages"] = len(_segments_from_mask(df["Brake"].astype(bool)))

    if "Throttle" in df.columns:
        m = (df["Throttle"] >= seuil_throttle).fillna(False).to_numpy(dtype=bool)
        dist = float(pas[m].sum())
        res["distance_traction"] = dist
        res["part_traction"] = dist / total

    m = (df["Speed"] >= DEPLOY_TAPER_START_KMH).fillna(False).to_numpy(dtype=bool)
    dist = float(pas[m].sum())
    res["distance_au_dela_taper"] = dist
    res["part_au_dela_taper"] = dist / total

    return res


def comparaison_proxys_energie(
    tel_par_pilote: dict[str, pd.DataFrame],
    pilotes: list[str] | None = None,
    seuil_throttle: float = 90.0,
) -> pd.DataFrame:
    """Applique `resume_proxys_energie` à plusieurs pilotes.

    Retour
    ------
    DataFrame trié par part de traction décroissante, une ligne par pilote.
    Vide si aucune télémétrie exploitable.
    """
    if not tel_par_pilote:
        return pd.DataFrame()

    codes = pilotes if pilotes else sorted(tel_par_pilote.keys())
    rows = []
    for code in codes:
        tel = tel_par_pilote.get(code)
        if tel is None or getattr(tel, "empty", True):
            continue
        resume = resume_proxys_energie(tel, seuil_throttle=seuil_throttle)
        if resume["distance_tour"] <= 0:
            continue
        rows.append({"Pilote": code, **resume})

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("part_traction", ascending=False).reset_index(drop=True)
