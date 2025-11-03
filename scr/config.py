import streamlit as st
import fastf1

def configure_page_home(title: str = "F1 Analytics"):
    fastf1.Cache.enable_cache('cache')
    st.set_page_config(
        page_title=title,
        layout="centered",
        initial_sidebar_state="expanded",
    )

def configure_page(title: str = "F1 Analytics"):
    fastf1.Cache.enable_cache('cache')
    st.set_page_config(
        page_title=title,
        layout="wide",
        initial_sidebar_state="expanded",
    )
