"""Page de diagnostic temporaire — à retirer après usage."""
import os, sys, tempfile, socket, traceback
from pathlib import Path
import streamlit as st

st.title("Diagnostic environnement")
st.write("**Python**", sys.version)

st.subheader("Cache FastF1")
from src.config import _CACHE_DIR
st.write("chemin:", str(_CACHE_DIR))
st.write("existe:", _CACHE_DIR.exists())
try:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = _CACHE_DIR / "ecriture_test.txt"
    p.write_text("ok"); p.unlink()
    st.success("écriture OK dans le cache")
except Exception as e:
    st.error(f"écriture IMPOSSIBLE: {type(e).__name__}: {e}")

st.subheader("Réseau sortant")
for host in ["livetiming.formula1.com", "api.jolpi.ca", "ergast.com"]:
    try:
        with socket.create_connection((host, 443), timeout=6):
            st.success(f"{host}: joignable")
    except Exception as e:
        st.error(f"{host}: {type(e).__name__}")

st.subheader("Chargement FastF1 brut")
try:
    import fastf1
    fastf1.Cache.enable_cache(str(_CACHE_DIR))
    s = fastf1.get_session(2024, "Australian Grand Prix", "R")
    s.load(telemetry=False, weather=False, messages=False)
    st.success(f"laps chargés: {len(s.laps)}")
except Exception:
    st.error("échec chargement brut")
    st.code(traceback.format_exc())
