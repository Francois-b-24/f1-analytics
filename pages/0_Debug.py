"""Page de diagnostic — à supprimer après résolution."""
import streamlit as st
import traceback
import fastf1
from src.config import configure_page
from src.ui import selections_courantes

configure_page("Debug")
st.subheader("Diagnostic télémétrie")

annee, grand_prix, session_type, loaded = selections_courantes(required=False)
if not loaded:
    st.warning("Charge d'abord une session sur Home.")
    st.stop()

st.write(f"Session : {annee} / {grand_prix} / {session_type}")

# --- Test direct fastf1, hors cache Streamlit ---
st.divider()
st.subheader("Test direct FastF1 (hors cache Streamlit)")
try:
    sess = fastf1.get_session(annee, grand_prix, session_type)
    st.write(f"f1_api_support : **{sess.f1_api_support}**")
    with st.spinner("sess.load()..."):
        sess.load()
    st.write(f"_car_data présent : **{hasattr(sess, '_car_data')}**")
    st.write(f"_pos_data présent : **{hasattr(sess, '_pos_data')}**")

    if hasattr(sess, '_car_data') and sess._car_data:
        st.success(f"car_data OK — {len(sess._car_data)} pilotes")
        # Test HAM
        drv_test = 'HAM' if 'HAM' in sess.laps['Driver'].values else sess.laps['Driver'].iloc[0]
        laps = sess.laps.pick_drivers(drv_test)
        st.write(f"Laps pour {drv_test} : {len(laps)}")
        lap = laps.pick_fastest()
        st.write(f"Type lap : {type(lap).__name__}, lap.session is sess : {lap.session is sess}")
        car = lap.get_car_data().add_distance()
        st.write(f"car_data shape : {car.shape}, cols : {list(car.columns)}")
        pos = lap.get_pos_data()
        st.write(f"pos_data shape : {pos.shape}, cols : {list(pos.columns)}")
        st.success("Extraction manuelle OK !")
    else:
        st.error("_car_data absent ou vide après sess.load()")
        st.write("Cela signifie que FastF1 ne peut pas charger la télémétrie pour cette session.")
        st.write("Causes possibles : session trop récente, données pas encore publiées, f1_api_support=False")

except Exception as e:
    st.error(f"Erreur : {type(e).__name__}: {e}")
    st.code(traceback.format_exc())

st.divider()
st.subheader("Cache Streamlit (_chargement_dataframes)")
from src.data import _chargement_dataframes
try:
    data = _chargement_dataframes(annee, grand_prix, session_type)
    tel = data.get("tel_par_pilote", {})
    st.write(f"tel_par_pilote : {len(tel)} pilotes — {sorted(tel.keys())}")
    if not tel:
        st.error("tel_par_pilote VIDE même après cache miss.")
except Exception as e:
    st.error(f"{type(e).__name__}: {e}")
    st.code(traceback.format_exc())
