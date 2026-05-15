"""Page de diagnostic — à supprimer après résolution."""
import streamlit as st
from src.config import configure_page
from src.ui import selections_courantes

configure_page("Debug")
st.subheader("Diagnostic télémétrie")

annee, grand_prix, session_type, loaded = selections_courantes(required=False)
if not loaded:
    st.warning("Charge d'abord une session sur Home.")
    st.stop()

st.write(f"Session : {annee} / {grand_prix} / {session_type}")

from src.data import _chargement_dataframes
import traceback

with st.spinner("Chargement..."):
    try:
        data = _chargement_dataframes(annee, grand_prix, session_type)
    except Exception as e:
        st.error(f"_chargement_dataframes a échoué : {e}")
        st.code(traceback.format_exc())
        st.stop()

tel = data.get("tel_par_pilote", {})
best = data.get("best_laps", {})
pilotes = data.get("pilotes", [])

st.write(f"**Pilotes dans data['pilotes']** ({len(pilotes)}) : {pilotes}")
st.write(f"**Clés tel_par_pilote** ({len(tel)}) : {sorted(tel.keys())}")
st.write(f"**Clés best_laps** ({len(best)}) : {sorted(best.keys())}")

if tel:
    drv = sorted(tel.keys())[0]
    st.write(f"**Exemple [{drv}]** shape={tel[drv].shape}, cols={list(tel[drv].columns)}")
else:
    st.error("tel_par_pilote est VIDE — l'extraction a échoué.")

st.divider()
st.write("**Session state keys (f1_sess)** :")
sess_keys = [k for k in st.session_state if "_f1_sess_" in k]
for k in sess_keys:
    sess = st.session_state[k]
    has_car = hasattr(sess, "_car_data")
    has_pos = hasattr(sess, "_pos_data")
    st.write(f"  {k} → _car_data={has_car}, _pos_data={has_pos}")
