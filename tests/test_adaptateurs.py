"""Tests des adaptateurs OpenF1 → DataFrames de l'application.

100 % hors ligne : les réponses de l'API sont figées dans des fixtures, copiées
sur des enregistrements réels (GP de Belgique 2026). Ces tests verrouillent le
contrat que les pages consomment — colonnes, types, unités.
"""
import numpy as np
import pandas as pd
import pytest

from src.adaptateurs import (
    ajouter_positions,
    construire_meteo,
    construire_resultats,
    construire_telemetrie,
    construire_tours,
)


@pytest.fixture
def pilotes():
    return [
        {"driver_number": 1, "name_acronym": "VER", "team_name": "Red Bull Racing",
         "broadcast_name": "M VERSTAPPEN", "full_name": "Max VERSTAPPEN",
         "team_colour": "3671C6"},
        {"driver_number": 4, "name_acronym": "NOR", "team_name": "McLaren",
         "broadcast_name": "L NORRIS", "full_name": "Lando NORRIS",
         "team_colour": "F47600"},
    ]


@pytest.fixture
def tours_bruts():
    return [
        {"driver_number": 1, "lap_number": 1, "lap_duration": 112.5,
         "duration_sector_1": 32.1, "duration_sector_2": 50.9, "duration_sector_3": 29.5,
         "date_start": "2026-07-19T13:03:52.073000+00:00", "is_pit_out_lap": False},
        {"driver_number": 1, "lap_number": 2, "lap_duration": 111.2,
         "duration_sector_1": 31.8, "duration_sector_2": 50.2, "duration_sector_3": 29.2,
         "date_start": "2026-07-19T13:05:44.573000+00:00", "is_pit_out_lap": False},
        {"driver_number": 4, "lap_number": 1, "lap_duration": 113.0,
         "duration_sector_1": 32.5, "duration_sector_2": 51.0, "duration_sector_3": 29.5,
         "date_start": "2026-07-19T13:03:53.000000+00:00", "is_pit_out_lap": False},
        # Tour sans chrono : fréquent (tour d'entrée aux stands, drapeau rouge)
        {"driver_number": 4, "lap_number": 2, "lap_duration": None,
         "duration_sector_1": None, "duration_sector_2": None, "duration_sector_3": None,
         "date_start": "2026-07-19T13:05:46.000000+00:00", "is_pit_out_lap": False},
    ]


@pytest.fixture
def relais_bruts():
    return [
        {"driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 2,
         "compound": "MEDIUM", "tyre_age_at_start": 0},
        {"driver_number": 4, "stint_number": 1, "lap_start": 1, "lap_end": 2,
         "compound": "HARD", "tyre_age_at_start": 3},
    ]


def test_construire_tours_colonnes_et_valeurs(tours_bruts, pilotes, relais_bruts):
    df = construire_tours(tours_bruts, pilotes, relais_bruts)

    assert len(df) == 4
    assert set(df["Driver"]) == {"VER", "NOR"}

    # Colonnes attendues par les pages et par src.analytics
    for colonne in ("Driver", "LapNumber", "LapTime", "LapSeconds", "Compound",
                    "Stint", "TyreLife", "Sector1TimeSec", "IsPersonalBest"):
        assert colonne in df.columns, f"colonne manquante: {colonne}"

    ver = df[(df["Driver"] == "VER") & (df["LapNumber"] == 2)].iloc[0]
    assert ver["LapSeconds"] == pytest.approx(111.2)
    assert ver["LapTime"] == pd.Timedelta(seconds=111.2)
    assert ver["Compound"] == "MEDIUM"
    assert ver["Team"] == "Red Bull Racing"


def test_tyre_life_suit_age_initial(tours_bruts, pilotes, relais_bruts):
    """L'âge du pneu part de `tyre_age_at_start` et s'incrémente par tour."""
    df = construire_tours(tours_bruts, pilotes, relais_bruts)

    ver = df[df["Driver"] == "VER"].sort_values("LapNumber")
    assert list(ver["TyreLife"]) == [1, 2]          # pneus neufs

    nor = df[df["Driver"] == "NOR"].sort_values("LapNumber")
    assert list(nor["TyreLife"]) == [4, 5]          # 3 tours déjà parcourus


def test_meilleur_tour_personnel(tours_bruts, pilotes, relais_bruts):
    """Un seul meilleur tour par pilote, sur le chrono le plus bas."""
    df = construire_tours(tours_bruts, pilotes, relais_bruts)

    meilleurs = df[df["IsPersonalBest"]]
    assert len(meilleurs) == 2
    assert meilleurs[meilleurs["Driver"] == "VER"]["LapNumber"].iloc[0] == 2
    # NOR n'a qu'un tour chronométré : c'est forcément son meilleur
    assert meilleurs[meilleurs["Driver"] == "NOR"]["LapNumber"].iloc[0] == 1


def test_tours_sans_chrono_conserves(tours_bruts, pilotes, relais_bruts):
    """Les tours sans chrono restent présents, avec LapSeconds à NaN."""
    df = construire_tours(tours_bruts, pilotes, relais_bruts)

    sans_chrono = df[(df["Driver"] == "NOR") & (df["LapNumber"] == 2)].iloc[0]
    assert pd.isna(sans_chrono["LapSeconds"])
    assert pd.isna(sans_chrono["LapTime"])
    assert not sans_chrono["IsPersonalBest"]


def test_arrets_marquent_pit_in_et_out(tours_bruts, pilotes, relais_bruts):
    """Un arrêt marque PitInTime au tour d'entrée et PitOutTime au suivant."""
    arrets = [{"driver_number": 1, "lap_number": 1, "pit_duration": 24.3}]
    df = construire_tours(tours_bruts, pilotes, relais_bruts, arrets)

    ver = df[df["Driver"] == "VER"].sort_values("LapNumber")
    assert pd.notna(ver.iloc[0]["PitInTime"])    # tour 1 : entrée
    assert pd.notna(ver.iloc[1]["PitOutTime"])   # tour 2 : sortie


def test_construire_tours_entree_vide(pilotes):
    df = construire_tours([], pilotes)
    assert df.empty
    assert "Driver" in df.columns  # colonnes typées même à vide


def test_construire_meteo():
    meteo = [
        {"date": "2026-07-19T13:00:00+00:00", "air_temperature": 18.1,
         "track_temperature": 35.9, "wind_speed": 1.6, "humidity": 50.2},
        {"date": "2026-07-19T13:01:00+00:00", "air_temperature": 18.3,
         "track_temperature": 36.2, "wind_speed": 2.0, "humidity": 49.8},
    ]
    df = construire_meteo(meteo, "2026-07-19T13:00:00+00:00")

    assert list(df["AirTemp"]) == [18.1, 18.3]
    # SessionTimeSec est l'écart au départ, en secondes
    assert list(df["SessionTimeSec"]) == [0.0, 60.0]


def test_construire_meteo_vide():
    assert construire_meteo([]).empty


def test_construire_resultats(pilotes):
    resultats = [
        {"position": 1, "driver_number": 4, "points": 25.0, "number_of_laps": 44,
         "duration": 5082.479, "dnf": False, "dns": False, "dsq": False},
        {"position": 2, "driver_number": 1, "points": 18.0, "number_of_laps": 44,
         "duration": 5090.1, "dnf": False, "dns": False, "dsq": False},
    ]
    df = construire_resultats(resultats, pilotes)

    assert list(df["Position"]) == [1, 2]
    assert df.iloc[0]["BroadcastName"] == "L NORRIS"
    assert df.iloc[0]["TeamName"] == "McLaren"
    assert (df["Status"] == "Terminé").all()


def test_construire_resultats_statuts(pilotes):
    """Abandon, disqualification et non-partant sont distingués."""
    resultats = [
        {"position": 1, "driver_number": 4, "dnf": True, "dns": False, "dsq": False},
        {"position": 2, "driver_number": 1, "dnf": False, "dns": False, "dsq": True},
    ]
    df = construire_resultats(resultats, pilotes)
    assert set(df["Status"]) == {"Abandon", "Disqualifié"}


def test_construire_resultats_qualifications(pilotes):
    """En qualifications, `duration` est une liste (Q1/Q2/Q3) : on garde le meilleur."""
    resultats = [
        {"position": 1, "driver_number": 4, "duration": [80.5, 79.8, 79.1],
         "dnf": False, "dns": False, "dsq": False},
    ]
    df = construire_resultats(resultats, pilotes)
    assert df.iloc[0]["Time"] == pd.Timedelta(seconds=79.1)


def test_construire_telemetrie():
    """Distance intégrée depuis la vitesse ; frein converti en booléen."""
    car = [
        {"date": "2026-07-19T13:00:00.000000+00:00", "speed": 360, "rpm": 11000,
         "n_gear": 8, "throttle": 100, "brake": 0, "drs": 0},
        {"date": "2026-07-19T13:00:01.000000+00:00", "speed": 360, "rpm": 11200,
         "n_gear": 8, "throttle": 100, "brake": 0, "drs": 0},
        {"date": "2026-07-19T13:00:02.000000+00:00", "speed": 180, "rpm": 9000,
         "n_gear": 4, "throttle": 0, "brake": 100, "drs": 0},
    ]
    position = [
        {"date": "2026-07-19T13:00:00.000000+00:00", "x": 100, "y": 200, "z": 0},
        {"date": "2026-07-19T13:00:01.000000+00:00", "x": 200, "y": 210, "z": 0},
        {"date": "2026-07-19T13:00:02.000000+00:00", "x": 300, "y": 220, "z": 0},
    ]
    df = construire_telemetrie(car, position)

    assert list(df.columns) == ["Distance", "Speed", "nGear", "Brake",
                                "Throttle", "RPM", "DRS", "X", "Y"]
    # Intégration par trapèzes : 360 km/h = 100 m/s, donc 100 m sur la première
    # seconde à vitesse constante. Sur la seconde suivante la voiture freine de
    # 360 à 180 km/h, soit une moyenne de 270 km/h = 75 m/s → 175 m cumulés.
    assert df["Distance"].iloc[1] == pytest.approx(100.0, abs=1)
    assert df["Distance"].iloc[2] == pytest.approx(175.0, abs=1)
    # Le frein OpenF1 (0/100) devient un booléen
    assert df["Brake"].tolist() == [False, False, True]
    assert df["X"].notna().all()


def test_construire_telemetrie_sans_position():
    """Sans données de position, la télémétrie reste exploitable (sans X/Y)."""
    car = [{"date": "2026-07-19T13:00:00+00:00", "speed": 100, "rpm": 9000,
            "n_gear": 5, "throttle": 50, "brake": 0, "drs": 0}]
    df = construire_telemetrie(car, [])
    assert not df.empty
    assert "X" not in df.columns


def test_construire_telemetrie_vide():
    assert construire_telemetrie([], []).empty


def test_ajouter_positions():
    """La position d'un tour est le dernier classement connu à son départ."""
    tours = pd.DataFrame({
        "Driver": ["VER", "VER"],
        "DriverNumber": [1, 1],
        "LapNumber": [1, 2],
        "DateDebut": ["2026-07-19T13:05:00+00:00", "2026-07-19T13:07:00+00:00"],
        "Position": [np.nan, np.nan],
    })
    positions = [
        {"driver_number": 1, "position": 3, "date": "2026-07-19T13:04:00+00:00"},
        {"driver_number": 1, "position": 2, "date": "2026-07-19T13:06:00+00:00"},
    ]
    df = ajouter_positions(tours, positions)

    assert df[df["LapNumber"] == 1]["Position"].iloc[0] == 3
    assert df[df["LapNumber"] == 2]["Position"].iloc[0] == 2


def test_ajouter_positions_sans_donnees():
    """Sans relevés de position, le DataFrame est renvoyé inchangé."""
    tours = pd.DataFrame({
        "Driver": ["VER"], "DriverNumber": [1], "LapNumber": [1],
        "DateDebut": ["2026-07-19T13:05:00+00:00"], "Position": [np.nan],
    })
    assert ajouter_positions(tours, []).equals(tours)
