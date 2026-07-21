"""Conversion des réponses OpenF1 vers les DataFrames attendus par l'app.

L'application a été bâtie sur les structures de FastF1 : les pages et
`src.analytics` consomment des colonnes précises (`Driver`, `LapNumber`,
`LapTime`, `Compound`, `TyreLife`…). Ce module traduit les données OpenF1 vers
ce même vocabulaire, ce qui permet de changer de source sans modifier les pages.

Fonctions pures : elles prennent des listes de dictionnaires (retour de
`src.openf1`) et rendent des DataFrames. Aucun appel réseau, donc testables
hors ligne sur des réponses figées.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("f1_analytics.adaptateurs")

# Colonnes du DataFrame `tours`, alignées sur ce que consomment les pages.
COLONNES_TOURS = [
    "Driver", "DriverNumber", "Team", "LapNumber", "LapTime", "LapSeconds",
    "Sector1TimeSec", "Sector2TimeSec", "Sector3TimeSec",
    "Compound", "Stint", "TyreLife", "PitInTime", "PitOutTime",
    "IsPersonalBest", "Position",
]


def _index_pilotes(pilotes: list[dict]) -> dict[int, dict]:
    """Indexe les pilotes par numéro, pour joindre acronyme et équipe."""
    index = {}
    for p in pilotes:
        numero = p.get("driver_number")
        if numero is not None:
            index[int(numero)] = p
    return index


def _acronyme(pilote: dict | None, numero: int) -> str:
    """Code 3 lettres du pilote, avec repli sur le numéro si absent."""
    if pilote:
        for champ in ("name_acronym", "last_name", "full_name"):
            valeur = pilote.get(champ)
            if valeur:
                return str(valeur)[:3].upper()
    return f"#{numero}"


def _relais_par_tour(relais: list[dict]) -> dict[tuple[int, int], dict]:
    """Associe chaque (pilote, tour) à son relais.

    OpenF1 décrit les relais par intervalles `lap_start`..`lap_end` ; les pages
    attendent une information par tour (composé, numéro de relais, âge du pneu).
    """
    table: dict[tuple[int, int], dict] = {}
    for r in relais:
        numero = r.get("driver_number")
        debut, fin = r.get("lap_start"), r.get("lap_end")
        if numero is None or debut is None or fin is None:
            continue
        age_initial = r.get("tyre_age_at_start") or 0
        for tour in range(int(debut), int(fin) + 1):
            table[(int(numero), tour)] = {
                "Compound": r.get("compound"),
                "Stint": r.get("stint_number"),
                # Âge du pneu à ce tour = âge au début du relais + tours parcourus
                "TyreLife": age_initial + (tour - int(debut)) + 1,
            }
    return table


def _arrets_par_tour(arrets: list[dict]) -> dict[tuple[int, int], float]:
    """Durée d'arrêt indexée par (pilote, tour)."""
    table: dict[tuple[int, int], float] = {}
    for a in arrets:
        numero, tour = a.get("driver_number"), a.get("lap_number")
        if numero is None or tour is None:
            continue
        duree = a.get("pit_duration") or a.get("lane_duration")
        if duree is not None:
            table[(int(numero), int(tour))] = float(duree)
    return table


def construire_tours(
    tours: list[dict],
    pilotes: list[dict],
    relais: list[dict] | None = None,
    arrets: list[dict] | None = None,
) -> pd.DataFrame:
    """Construit le DataFrame `tours` au format attendu par l'application.

    Paramètres
    ----------
    tours, pilotes, relais, arrets
        Retours bruts de `src.openf1`.

    Retour
    ------
    DataFrame aux colonnes `COLONNES_TOURS`. Vide (mais typé) si aucune donnée.
    """
    if not tours:
        return pd.DataFrame(columns=COLONNES_TOURS)

    index_pilotes = _index_pilotes(pilotes or [])
    table_relais = _relais_par_tour(relais or [])
    table_arrets = _arrets_par_tour(arrets or [])

    lignes = []
    for t in tours:
        numero = t.get("driver_number")
        tour = t.get("lap_number")
        if numero is None or tour is None:
            continue
        numero, tour = int(numero), int(tour)
        pilote = index_pilotes.get(numero)
        duree = t.get("lap_duration")
        infos_relais = table_relais.get((numero, tour), {})

        # Un arrêt est rattaché au tour d'entrée ; le tour suivant est la sortie.
        duree_arret = table_arrets.get((numero, tour))
        sortie_stand = t.get("is_pit_out_lap") or (numero, tour - 1) in table_arrets

        lignes.append({
            "Driver": _acronyme(pilote, numero),
            "DriverNumber": numero,
            "Team": (pilote or {}).get("team_name"),
            "LapNumber": tour,
            "LapTime": pd.to_timedelta(duree, unit="s") if duree else pd.NaT,
            "LapSeconds": float(duree) if duree else np.nan,
            "Sector1TimeSec": t.get("duration_sector_1"),
            "Sector2TimeSec": t.get("duration_sector_2"),
            "Sector3TimeSec": t.get("duration_sector_3"),
            "Compound": infos_relais.get("Compound"),
            "Stint": infos_relais.get("Stint"),
            "TyreLife": infos_relais.get("TyreLife"),
            # Les pages testent la présence (notna) de ces colonnes, pas leur valeur.
            "PitInTime": pd.to_timedelta(duree_arret, unit="s") if duree_arret else pd.NaT,
            "PitOutTime": pd.Timedelta(0) if sortie_stand else pd.NaT,
            "DateDebut": t.get("date_start"),
            "Position": np.nan,
        })

    df = pd.DataFrame(lignes)
    if df.empty:
        return pd.DataFrame(columns=COLONNES_TOURS)

    # Meilleur tour personnel — colonne attendue par la page Chronos.
    df["IsPersonalBest"] = False
    valides = df["LapSeconds"].notna()
    if valides.any():
        meilleurs = df[valides].groupby("Driver")["LapSeconds"].idxmin()
        df.loc[meilleurs, "IsPersonalBest"] = True

    return df.sort_values(["Driver", "LapNumber"]).reset_index(drop=True)


def ajouter_positions(tours: pd.DataFrame, positions: list[dict]) -> pd.DataFrame:
    """Renseigne la colonne `Position` de chaque tour.

    OpenF1 publie les positions horodatées, pas par tour : on rapproche chaque
    tour du dernier classement connu à son heure de départ. Nécessaire au
    graphique d'évolution des positions (page Performances).
    """
    if tours.empty or not positions or "DateDebut" not in tours.columns:
        return tours

    pos = pd.DataFrame([{
        "DriverNumber": p.get("driver_number"),
        "PositionRelevee": p.get("position"),
        "_t": p.get("date"),
    } for p in positions])
    pos["_t"] = pd.to_datetime(pos["_t"], format="ISO8601", utc=True, errors="coerce")
    pos = pos.dropna(subset=["_t", "DriverNumber"]).sort_values("_t")
    if pos.empty:
        return tours

    df = tours.copy()
    df["_t"] = pd.to_datetime(df["DateDebut"], format="ISO8601", utc=True, errors="coerce")
    manquants = df["_t"].isna()
    if manquants.all():
        return tours

    # merge_asof exige un tri global sur la clé temporelle.
    df = df.sort_values("_t")
    pos["DriverNumber"] = pos["DriverNumber"].astype("int64")
    df["DriverNumber"] = df["DriverNumber"].astype("int64")

    fusion = pd.merge_asof(
        df[~manquants], pos, on="_t", by="DriverNumber", direction="backward",
    )
    fusion["Position"] = fusion["PositionRelevee"]
    fusion = fusion.drop(columns=["PositionRelevee"])

    resultat = pd.concat([fusion, df[manquants]], ignore_index=True)
    return (
        resultat.drop(columns=["_t"])
        .sort_values(["Driver", "LapNumber"])
        .reset_index(drop=True)
    )


def construire_meteo(meteo: list[dict], depart_session: str | None = None) -> pd.DataFrame:
    """Construit le DataFrame météo (AirTemp, TrackTemp, WindSpeed…).

    `SessionTimeSec` est l'écart en secondes depuis le début de la session : la
    page Météo l'utilise comme axe des abscisses.
    """
    if not meteo:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "AirTemp": m.get("air_temperature"),
        "TrackTemp": m.get("track_temperature"),
        "WindSpeed": m.get("wind_speed"),
        "WindDirection": m.get("wind_direction"),
        "Humidity": m.get("humidity"),
        "Pressure": m.get("pressure"),
        "Rainfall": m.get("rainfall"),
        "Date": m.get("date"),
    } for m in meteo])

    horodatage = pd.to_datetime(df["Date"], format="ISO8601", utc=True, errors="coerce")
    origine = (
        pd.to_datetime(depart_session, format="ISO8601", utc=True, errors="coerce")
        if depart_session else horodatage.min()
    )
    if pd.isna(origine):
        origine = horodatage.min()
    df["SessionTimeSec"] = (horodatage - origine).dt.total_seconds()

    return df.sort_values("SessionTimeSec").reset_index(drop=True)


def construire_resultats(resultats: list[dict], pilotes: list[dict]) -> pd.DataFrame:
    """Construit le classement final au format attendu (Position, Points…)."""
    if not resultats:
        return pd.DataFrame()

    index_pilotes = _index_pilotes(pilotes or [])
    lignes = []
    for r in resultats:
        numero = r.get("driver_number")
        if numero is None:
            continue
        numero = int(numero)
        pilote = index_pilotes.get(numero, {})
        duree = r.get("duration")

        # `duration` vaut une liste par pilote en qualifications (Q1/Q2/Q3).
        if isinstance(duree, list):
            valides = [d for d in duree if d]
            duree = min(valides) if valides else None

        if r.get("dsq"):
            statut = "Disqualifié"
        elif r.get("dns"):
            statut = "Non partant"
        elif r.get("dnf"):
            statut = "Abandon"
        else:
            statut = "Terminé"

        lignes.append({
            "Position": r.get("position"),
            "DriverNumber": numero,
            "Abbreviation": _acronyme(pilote, numero),
            "BroadcastName": pilote.get("broadcast_name") or _acronyme(pilote, numero),
            "FullName": pilote.get("full_name"),
            "TeamName": pilote.get("team_name"),
            "TeamColor": pilote.get("team_colour"),
            "Points": r.get("points"),
            "Status": statut,
            "Laps": r.get("number_of_laps"),
            "Time": pd.to_timedelta(duree, unit="s") if duree else pd.NaT,
            "GapToLeader": r.get("gap_to_leader"),
        })

    df = pd.DataFrame(lignes)
    if df.empty:
        return df
    return df.sort_values("Position", na_position="last").reset_index(drop=True)


def construire_telemetrie(car: list[dict], position: list[dict]) -> pd.DataFrame:
    """Assemble télémétrie et position d'un tour en un DataFrame unique.

    `Distance` n'est pas fournie par OpenF1 : elle est intégrée depuis la
    vitesse et l'horodatage, comme le fait FastF1.

    Colonnes produites : Distance, Speed, nGear, Brake, Throttle, RPM, DRS, X, Y.
    """
    if not car:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "Speed": c.get("speed"),
        "RPM": c.get("rpm"),
        "nGear": c.get("n_gear"),
        "Throttle": c.get("throttle"),
        # OpenF1 code le frein en pourcentage ; les pages attendent un booléen.
        "Brake": bool(c.get("brake")) if c.get("brake") is not None else False,
        "DRS": c.get("drs"),
        "Date": c.get("date"),
    } for c in car])

    horodatage = pd.to_datetime(df["Date"], format="ISO8601", utc=True, errors="coerce")
    df = df.assign(_t=horodatage).sort_values("_t").reset_index(drop=True)

    # Distance = intégrale de la vitesse sur le temps (v en km/h -> m/s).
    # On intègre par la méthode des trapèzes : sur un intervalle, la distance
    # dépend de la vitesse MOYENNE entre les deux points, pas de la vitesse
    # instantanée d'arrivée — sinon un freinage écrase la distance parcourue.
    secondes = (df["_t"] - df["_t"].iloc[0]).dt.total_seconds().to_numpy()
    vitesse_ms = pd.to_numeric(df["Speed"], errors="coerce").fillna(0).to_numpy() / 3.6

    distance = np.zeros(len(df))
    if len(df) > 1:
        pas = np.diff(secondes)
        vitesse_moyenne = (vitesse_ms[1:] + vitesse_ms[:-1]) / 2.0
        distance[1:] = np.cumsum(vitesse_moyenne * pas)
    df["Distance"] = distance

    # Position X/Y rapprochée par horodatage le plus proche.
    if position:
        pos = pd.DataFrame([{
            "X": p.get("x"), "Y": p.get("y"), "Z": p.get("z"), "Date": p.get("date"),
        } for p in position])
        pos["_t"] = pd.to_datetime(pos["Date"], format="ISO8601", utc=True, errors="coerce")
        pos = pos.dropna(subset=["_t"]).sort_values("_t").reset_index(drop=True)
        if not pos.empty:
            df = pd.merge_asof(
                df, pos[["_t", "X", "Y"]], on="_t", direction="nearest",
                tolerance=pd.Timedelta("1s"),
            )

    colonnes = [c for c in ("Distance", "Speed", "nGear", "Brake", "Throttle",
                            "RPM", "DRS", "X", "Y") if c in df.columns]
    return df[colonnes].reset_index(drop=True)
