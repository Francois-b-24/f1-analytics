import numpy as np
import pandas as pd
import pytest

from src.analytics import (
    sector_times_long,
    sector_best_per_driver,
    stint_degradation,
    stint_degradation_fits,
    delta_time_vs_distance,
    tyre_degradation_matrix,
    phases_telemetrie,
    resume_proxys_energie,
    comparaison_proxys_energie,
)


@pytest.fixture
def fake_tours():
    return pd.DataFrame(
        {
            "Driver": ["HAM"] * 6 + ["VER"] * 6,
            "LapNumber": list(range(1, 7)) * 2,
            "Stint": [1] * 6 + [1] * 6,
            "Compound": ["SOFT"] * 6 + ["MEDIUM"] * 6,
            "LapSeconds": [90.5, 90.3, 90.6, 90.9, 91.2, 91.4,
                           91.0, 90.8, 90.9, 91.1, 91.4, 91.6],
            "Sector1TimeSec": [30.1, 30.0, 30.2, 30.3, 30.4, 30.5,
                               30.5, 30.4, 30.4, 30.5, 30.6, 30.7],
            "Sector2TimeSec": [28.2, 28.1, 28.2, 28.3, 28.4, 28.5,
                               28.3, 28.2, 28.3, 28.3, 28.4, 28.5],
            "Sector3TimeSec": [32.2, 32.2, 32.2, 32.3, 32.4, 32.4,
                               32.2, 32.2, 32.2, 32.3, 32.4, 32.4],
            "PitInTime": [pd.NaT] * 12,
            "PitOutTime": [pd.NaT] * 12,
        }
    )


def test_sector_times_long(fake_tours):
    long = sector_times_long(fake_tours)
    assert set(long["Sector"].unique()) == {"S1", "S2", "S3"}
    assert len(long) == 12 * 3
    assert (long["Seconds"] > 0).all()


def test_sector_best_per_driver(fake_tours):
    best = sector_best_per_driver(fake_tours)
    assert set(best["Driver"]) == {"HAM", "VER"}
    # HAM is faster on S1 and S2, tie-ish S3 → total HAM < VER
    ham = best[best["Driver"] == "HAM"].iloc[0]
    ver = best[best["Driver"] == "VER"].iloc[0]
    assert ham["Total"] < ver["Total"]
    assert ham["DeltaTotal"] == 0.0


def test_stint_degradation_fits_slope_positive(fake_tours):
    deg = stint_degradation(fake_tours, min_laps=3)
    fits = stint_degradation_fits(deg)
    assert not fits.empty
    # With monotonically increasing lap times, slope should be positive
    assert (fits["Slope"] > 0).all()


def test_delta_time_vs_distance_faster_ref_negative_delta():
    # Ref faster than cmp by 2 km/h over 5 km → cmp should be "behind" (Delta > 0)
    tel_ref = pd.DataFrame({"Distance": np.linspace(0, 5000, 50), "Speed": np.full(50, 250.0)})
    tel_cmp = pd.DataFrame({"Distance": np.linspace(0, 5000, 50), "Speed": np.full(50, 248.0)})
    d = delta_time_vs_distance(tel_ref, tel_cmp)
    assert not d.empty
    # Final delta must be > 0 (cmp is slower → accumulates time deficit)
    assert d["Delta"].iloc[-1] > 0
    # Start delta is 0
    assert abs(d["Delta"].iloc[0]) < 1e-9


def test_tyre_degradation_matrix_shape(fake_tours):
    mat = tyre_degradation_matrix(fake_tours)
    assert mat.shape[0] == 2  # 2 drivers
    assert mat.shape[1] == 6  # 6 laps
    # Each driver has at least one cell equal to 0 (their PB)
    assert (mat.min(axis=1) == 0).all()


def test_empty_input_handling():
    empty = pd.DataFrame()
    assert sector_times_long(empty).empty
    assert sector_best_per_driver(empty).empty
    assert stint_degradation(empty).empty
    assert stint_degradation_fits(pd.DataFrame()).empty
    assert tyre_degradation_matrix(empty).empty
    assert delta_time_vs_distance(None, None).empty


# ---------------------------------------------------------------------------
# F5 — Proxys d'énergie 2026
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_tel():
    """Tour synthétique : traction 0-1000 m, freinage 1000-1500 m, traction 1500-2000 m.

    Pas d'échantillonnage constant de 10 m pour rendre les parts calculables à la main.
    """
    distance = np.arange(0, 2000, 10, dtype=float)
    throttle = np.where((distance < 1000) | (distance >= 1500), 100.0, 0.0)
    brake = (distance >= 1000) & (distance < 1500)
    # Vitesse : élevée en traction, chute au freinage
    speed = np.where(brake, 150.0, 300.0)
    return pd.DataFrame(
        {"Distance": distance, "Speed": speed, "Throttle": throttle, "Brake": brake}
    )


def test_phases_telemetrie(fake_tel):
    phases = phases_telemetrie(fake_tel)
    assert not phases.empty
    assert set(phases["Phase"].unique()) == {"Traction", "Freinage"}
    # 2 phases de traction (avant et après le freinage) + 1 freinage
    assert (phases["Phase"] == "Traction").sum() == 2
    assert (phases["Phase"] == "Freinage").sum() == 1
    # Les segments sont ordonnés par distance croissante
    assert phases["DistanceDebut"].is_monotonic_increasing
    # Le freinage commence bien vers 1000 m
    freinage = phases[phases["Phase"] == "Freinage"].iloc[0]
    assert freinage["DistanceDebut"] == pytest.approx(1000.0, abs=20)


def test_phases_telemetrie_filtre_segments_courts(fake_tel):
    # Avec un seuil supérieur à la longueur du freinage (500 m), il disparaît
    phases = phases_telemetrie(fake_tel, distance_min_m=600.0)
    assert (phases["Phase"] == "Freinage").sum() == 0


def test_resume_proxys_energie(fake_tel):
    r = resume_proxys_energie(fake_tel)
    # 500 m de freinage sur 2000 m de tour => 25 %
    assert r["part_freinage"] == pytest.approx(0.25, abs=0.02)
    # 1500 m de pleine traction => 75 %
    assert r["part_traction"] == pytest.approx(0.75, abs=0.02)
    assert r["nb_freinages"] == 1
    assert r["vitesse_max"] == 300.0
    # 300 km/h dépasse le seuil de décroissance (290) : toute la traction compte
    assert r["part_au_dela_taper"] == pytest.approx(0.75, abs=0.02)
    # Les parts restent des fractions
    for cle in ("part_freinage", "part_traction", "part_au_dela_taper"):
        assert 0.0 <= r[cle] <= 1.0


def test_comparaison_proxys_energie(fake_tel):
    lent = fake_tel.copy()
    lent["Throttle"] = 0.0  # aucune pleine traction
    df = comparaison_proxys_energie({"AAA": fake_tel, "BBB": lent})
    assert list(df["Pilote"]) == ["AAA", "BBB"]  # tri par part_traction décroissante
    assert df.loc[df["Pilote"] == "BBB", "part_traction"].iloc[0] == 0.0


def test_proxys_energie_entrees_vides():
    assert phases_telemetrie(pd.DataFrame()).empty
    assert phases_telemetrie(None).empty
    assert resume_proxys_energie(pd.DataFrame())["distance_tour"] == 0.0
    assert resume_proxys_energie(None)["distance_tour"] == 0.0
    assert comparaison_proxys_energie({}).empty
    # Un pilote sans télémétrie exploitable est ignoré, pas une erreur
    assert comparaison_proxys_energie({"XXX": pd.DataFrame()}).empty
