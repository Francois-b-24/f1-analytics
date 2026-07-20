"""Diagnostic approfondi — pourquoi load() ne remplit pas _laps."""
import traceback, logging, io
import streamlit as st
from src.config import _CACHE_DIR

st.title("Diagnostic 2 — chargement FastF1")

buf = io.StringIO()
h = logging.StreamHandler(buf); h.setLevel(logging.DEBUG)
for name in ("fastf1", "fastf1.core", "fastf1._api", "fastf1.req"):
    lg = logging.getLogger(name); lg.setLevel(logging.DEBUG); lg.addHandler(h)

import fastf1
fastf1.Cache.enable_cache(str(_CACHE_DIR))
s = fastf1.get_session(2024, "Australian Grand Prix", "R")
st.write("session obtenue:", s)
try:
    s.load(laps=True, telemetry=False, weather=False, messages=False)
    st.write("load() terminé sans exception")
except Exception:
    st.error("load() a levé"); st.code(traceback.format_exc())

st.write("_laps présent :", hasattr(s, "_laps"))
try:
    st.success(f"laps: {len(s.laps)}")
except Exception as e:
    st.error(f"laps inaccessible: {type(e).__name__}")

st.subheader("Logs FastF1 capturés")
st.code(buf.getvalue()[-6000:] or "(aucun log)")
