import numpy as np
import pandas as pd
import pytest

from scr.analytics import (
    sector_times_long,
    sector_best_per_driver,
    stint_degradation,
    stint_degradation_fits,
    delta_time_vs_distance,
    tyre_degradation_matrix,
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
