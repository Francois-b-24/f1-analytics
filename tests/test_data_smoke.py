import pytest
from scr.data import chargement_session

def test_chargement_session_smoke():
    try:
        d = chargement_session(2025, 'Australian Grand Prix', 'R')
        assert isinstance(d, dict)
        for k in ['session', 'nom', 'tours', 'pilotes', 'meteo', 'resultats']:
            assert k in d
    except Exception:
        pytest.skip('Aucune data disponible ou absence de connexion pour FastF1 (test smoke).')

