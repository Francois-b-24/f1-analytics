import pytest
import numpy as np
import pandas as pd
from scr.utils import formatage_timedelta, secs

def test_formatage_timedelta_none():
    assert formatage_timedelta(None) == '—'

def test_formatage_timedelta_nan():
    assert formatage_timedelta(pd.NaT) == '—'

def test_formatage_timedelta_standard():
    td = pd.Timedelta(seconds=95.123)
    assert formatage_timedelta(td) == '01:35.123'

def test_secs_none():
    assert np.isnan(secs(None))

def test_secs_nan():
    assert np.isnan(secs(pd.NaT))

def test_secs_standard():
    td = pd.Timedelta('0 days 00:02:05.123')
    assert abs(secs(td) - 125.123) < 1e-3

