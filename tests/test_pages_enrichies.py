"""Rendu des pages enrichies en phase 4 — hors ligne.

`chargement_session` est substitué depuis l'intérieur du script : AppTest
exécute celui-ci dans son propre module, et les pages importent les fonctions
par leur nom, donc un monkeypatch depuis le test ne les atteindrait pas. C'est
pour cela que `charger_session_ou_stopper` importe `chargement_session`
tardivement (cf. src/session.py).
"""
from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

# Session synthétique : deux pilotes, deux écuries, un arrêt chacun au tour 4,
# VER remonte de la 3e à la 1re place, HAM descend de la 1re à la 2e.
_SESSION = '''
import numpy as np
import pandas as pd
import src.data

_t = pd.DataFrame({
 "Driver":["VER"]*6+["HAM"]*6, "DriverNumber":[1]*6+[44]*6,
 "Team":["Red Bull"]*6+["Mercedes"]*6, "LapNumber":list(range(1,7))*2,
 "LapTime":pd.to_timedelta([80.1,79.8,79.5,80.2,79.9,79.7]*2, unit="s"),
 "LapSeconds":[80.1,79.8,79.5,80.2,79.9,79.7]*2,
 "Sector1TimeSec":[26.0]*12,"Sector2TimeSec":[27.0]*12,"Sector3TimeSec":[26.5]*12,
 "Compound":["SOFT"]*3+["HARD"]*3+["SOFT"]*3+["MEDIUM"]*3,
 "Stint":[1,1,1,2,2,2]*2,"TyreLife":[1,2,3,1,2,3]*2,
 "PitInTime":pd.to_timedelta([None,None,None,2.4,None,None,
                              None,None,None,3.1,None,None], unit="s"),
 "PitOutTime":[pd.NaT]*12,
 "IsPersonalBest":[False,False,True,False,False,False]*2,
 "Position":[3.0,2.0,1.0,1.0,1.0,1.0, 1.0,1.0,2.0,2.0,2.0,2.0],
})
_m = pd.DataFrame({"SessionTimeSec":[0,60,120],"AirTemp":[22.0,22.5,23.0],
                   "TrackTemp":[35.0,36.0,37.0],"WindSpeed":[1.0,1.2,0.9]})
_r = pd.DataFrame({"Position":[1,2],"Abbreviation":["VER","HAM"],
                   "TeamName":["Red Bull","Mercedes"],"Points":[25.0,18.0],
                   "Status":["Terminé"]*2,"Laps":[6,6]})
_bl = {c: {"LapNumber":3,"LapSeconds":79.5,"LapTimeStr":"1:19.500",
           "DriverNumber":(1 if c=="VER" else 44),
           "debut":"2024-01-01T00:00:00","duree":79.5,
           "Compound":"SOFT","Stint":1} for c in ("VER","HAM")}

src.data.chargement_session = lambda *a, **k: {
  "nom":"GP test","tours":_t.copy(),"pilotes":["VER","HAM"],"meteo":_m,
  "resultats":_r,"best_laps":_bl,"session_key":9999,"session":None}

import streamlit as st
for k, v in [("annee",2024),("grand_prix","GP test"),("session_type","@@SESSION@@"),
             ("loaded",True)]:
    st.session_state.setdefault(k, v)
'''


def _page(fichier: str, *, session: str = "R", sans_arrets: bool = False) -> AppTest:
    # Substitution d'un marqueur plutôt que str.format : le script contient des
    # dicts Python, dont les accolades seraient prises pour des champs à formater.
    prelude = _SESSION.replace("@@SESSION@@", session)
    if sans_arrets:
        prelude = prelude.replace(
            '"PitInTime":pd.to_timedelta([None,None,None,2.4,None,None,\n'
            '                              None,None,None,3.1,None,None], unit="s"),',
            '"PitInTime":[pd.NaT]*12,',
        )
    at = AppTest.from_string(prelude + "\n" + open(fichier).read(), default_timeout=60)
    at.run()
    return at


def _valeurs(at: AppTest) -> dict[str, str]:
    return {m.label: m.value for m in at.metric}


# --------------------------------------------------------------------------
# Arrêts aux stands
# --------------------------------------------------------------------------

def test_arrets_affiche_des_indicateurs():
    at = _page("pages/arrets.py")

    assert not at.exception
    valeurs = _valeurs(at)
    assert valeurs["Arrêts"] == "2"
    # Médiane de 2,4 et 3,1.
    assert valeurs["Durée médiane"] == "2.75 s"
    assert valeurs["Arrêt le plus rapide"] == "2.40 s"
    assert valeurs["Pilotes concernés"] == "2"


def test_arrets_sans_donnees_explique_au_lieu_de_planter():
    """Cas courant en essais libres, et en course avant publication."""
    at = _page("pages/arrets.py", sans_arrets=True)

    assert not at.exception
    assert any("Aucun arrêt" in i.value for i in at.info)
    assert not at.metric, "aucun indicateur ne doit s'afficher sans donnée"


def test_arrets_precise_que_la_duree_exclut_la_voie_des_stands():
    """Sans cette précision, le chiffre serait pris pour la perte totale."""
    at = _page("pages/arrets.py")

    assert any("voie des stands" in c.value for c in at.caption)


# --------------------------------------------------------------------------
# Positions par tour
# --------------------------------------------------------------------------

def test_positions_identifie_remontee_et_chute():
    at = _page("pages/positions.py")

    assert not at.exception
    valeurs = _valeurs(at)
    assert valeurs["Plus belle remontée"] == "VER"
    assert valeurs["Plus forte chute"] == "HAM"


def test_positions_compte_les_changements():
    at = _page("pages/positions.py")

    # VER : 3->2->1 (2 changements), HAM : 1->2 (1).
    assert _valeurs(at)["Changements de position"] == "3"


def test_positions_ne_promet_pas_des_depassements():
    """La donnée ne distingue pas un dépassement d'un arrêt aux stands."""
    at = _page("pages/positions.py")

    libelles = [m.label for m in at.metric]
    assert "Changements de position" in libelles
    assert not any("épassement" in label for label in libelles)


@pytest.mark.parametrize("session", ["Q", "FP1"])
def test_positions_hors_course_renvoie_vers_une_course(session):
    at = _page("pages/positions.py", session=session)

    assert not at.exception
    assert any("courses" in i.value for i in at.info)
    assert not at.metric


# --------------------------------------------------------------------------
# Exports
# --------------------------------------------------------------------------

def test_exports_previsualise_avant_telechargement():
    at = _page("pages/exports.py")

    assert not at.exception
    valeurs = _valeurs(at)
    assert valeurs["Lignes"] == "12"
    assert at.dataframe, "un aperçu doit être affiché"


def test_exports_expose_les_meilleurs_tours():
    """`best_laps` était dans le contrat de session mais jamais exporté."""
    at = _page("pages/exports.py")

    groupe = at.button_group[0]
    libelles = [str(o.content) for o in groupe.options]

    assert any("Meilleurs tours" in lib for lib in libelles)


def test_exports_change_de_jeu_de_donnees():
    at = _page("pages/exports.py")
    assert _valeurs(at)["Lignes"] == "12"

    apres = at.button_group[0].set_value(["Meilleurs tours"]).run()

    assert not apres.exception
    # Deux pilotes, donc deux meilleurs tours.
    assert _valeurs(apres)["Lignes"] == "2"
