import pandas as pd
from src.utils import formatage_timedelta

def test_formatage_timedelta_none():
    assert formatage_timedelta(None) == '—'

def test_formatage_timedelta_nan():
    assert formatage_timedelta(pd.NaT) == '—'

def test_formatage_timedelta_standard():
    td = pd.Timedelta(seconds=95.123)
    assert formatage_timedelta(td) == '01:35.123'
