import streamlit as st
import fastf1
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# =========================
# CONFIGURATION GLOBALE
# =========================
fastf1.Cache.enable_cache('cache')
st.set_page_config(
    page_title="F1 Analytics",
    layout="wide",
    initial_sidebar_state="expanded"  # => sidebar ouverte
)

# =========================
# UTILITAIRES
# =========================
def fmt_timedelta(td) -> str:
    """Formate un pandas.Timedelta ou None en mm:ss.ms."""
    if pd.isna(td):
        return "—"
    total_ms = int(td.total_seconds() * 1000)
    minutes, ms_rem = divmod(total_ms, 60_000)
    seconds, ms = divmod(ms_rem, 1000)
    return f"{minutes:02d}:{seconds:02d}.{ms:03d}"

def secs(td) -> float:
    """Convertit Timedelta en secondes (float)."""
    if pd.isna(td):
        return np.nan
    return td.total_seconds()


# =========================
# CACHE – Chargements
# =========================
@st.cache_data(show_spinner=False)
def load_session_data(year: int, event: str, sess_type: str):
    sess = fastf1.get_session(year, event, sess_type)
    sess.load()

    # Tours enrichis
    laps = sess.laps.copy().reset_index(drop=True)
    if 'LapTime' in laps:
        laps['LapSeconds'] = laps['LapTime'].apply(secs)
    for col in ['Sector1Time', 'Sector2Time', 'Sector3Time']:
        if col in laps:
            laps[col + 'Sec'] = laps[col].apply(secs)

    # Pilotes (abréviations présentes dans laps)
    driver_codes = sorted(laps['Driver'].dropna().unique().tolist())

    # Météo
    try:
        weather = sess.weather_data.copy().reset_index(drop=True)
        if 'Time' in weather:
            weather['SessionTimeSec'] = weather['Time'].apply(secs)
    except Exception:
        weather = pd.DataFrame()

    # Résultats (si dispo)
    try:
        results = sess.results.copy().reset_index(drop=True)
    except Exception:
        results = pd.DataFrame()

    return dict(
        name=sess.name,
        laps=laps,
        drivers=driver_codes,
        weather=weather,
        results=results,
    )

@st.cache_data(show_spinner=False)
def get_fastest_lap_and_tel(session_key: str, _laps_df: pd.DataFrame, driver_code: str):
    # `_laps_df` ignoré du hash => évite UnhashableParamError
    laps_d = _laps_df.pick_driver(driver_code)
    fastest = laps_d.pick_fastest()
    tel = fastest.get_car_data().add_distance()
    return fastest, tel

@st.cache_data(show_spinner=True)
def compute_driver_standings(year: int, upto_event: str) -> pd.DataFrame:
    """Calcule le classement pilotes cumulé jusqu’à l’épreuve choisie (en chargeant chaque course)."""
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception:
        return pd.DataFrame()
    if 'EventName' not in schedule:
        return pd.DataFrame()
    names = schedule['EventName'].tolist()
    if upto_event not in names:
        return pd.DataFrame()

    upto_idx = names.index(upto_event)
    chunks = []
    for i in range(upto_idx + 1):
        ev = schedule.iloc[i]
        try:
            s = fastf1.get_session(year, ev['EventName'], 'R')
            s.load()
            r = s.results.copy()
            if not r.empty and 'Abbreviation' in r and 'Points' in r:
                chunks.append(r[['Abbreviation', 'Points', 'TeamName']])
        except Exception:
            continue

    if not chunks:
        return pd.DataFrame()

    all_pts = pd.concat(chunks, ignore_index=True)
    standings = (all_pts.groupby(['Abbreviation', 'TeamName'], dropna=False)['Points']
                        .sum().reset_index())
    standings = standings.sort_values('Points', ascending=False).reset_index(drop=True)
    standings['Position'] = standings.index + 1
    return standings[['Position', 'Abbreviation', 'TeamName', 'Points']]

# Classement constructeurs cumulé jusqu'à l'épreuve choisie
@st.cache_data(show_spinner=True)
def compute_constructor_standings(year: int, upto_event: str) -> pd.DataFrame:
    """Calcule le classement constructeurs cumulé jusqu’à l’épreuve choisie."""
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception:
        return pd.DataFrame()
    if 'EventName' not in schedule:
        return pd.DataFrame()
    names = schedule['EventName'].tolist()
    if upto_event not in names:
        return pd.DataFrame()

    upto_idx = names.index(upto_event)
    chunks = []
    for i in range(upto_idx + 1):
        ev = schedule.iloc[i]
        try:
            s = fastf1.get_session(year, ev['EventName'], 'R')
            s.load()
            r = s.results.copy()
            if not r.empty and 'TeamName' in r and 'Points' in r:
                # Agrège par course pour éviter double comptage (mais somme suffit)
                chunks.append(r[['TeamName','Points']])
        except Exception:
            continue
    if not chunks:
        return pd.DataFrame()

    all_pts = pd.concat(chunks, ignore_index=True)
    standings = (all_pts.groupby(['TeamName'], dropna=False)['Points']
                        .sum().reset_index())
    standings = standings.sort_values('Points', ascending=False).reset_index(drop=True)
    standings['Position'] = standings.index + 1
    return standings[['Position','TeamName','Points']]

# =========================
# EN-TÊTE
# =========================
st.title("🏎️ F1 Analytics – FastF1")
st.markdown("Explorez interactivement les données F1 (tours, télémétrie, pneus, arrêts, météo) ✨")

# Hint pour indiquer la présence de la sidebar (affiché une seule fois)
if "sidebar_hint_ack" not in st.session_state:
    st.session_state["sidebar_hint_ack"] = False

if not st.session_state["sidebar_hint_ack"]:
    st.caption("👈 Astuce : tous les réglages sont dans la barre latérale à gauche.")
    st.button("Masquer ce message", on_click=lambda: st.session_state.update(sidebar_hint_ack=True))

# =========================
# SIDEBAR – Session & Navigation & Pilotes
# =========================
with st.sidebar:
    st.header("Session")
    year = st.selectbox("Saison", list(range(2018, datetime.now().year + 1))[::-1])

    # Liste officielle des événements
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        events = schedule['EventName'].tolist()
    except Exception:
        events = []
    event_name = st.selectbox("Grand Prix", options=events if events else ["Bahrain", "Monaco", "Monza"])
    session_type = st.selectbox("Type de session", ["FP1", "FP2", "FP3", "Q", "R"])

    # State de chargement persistant
    if "loaded" not in st.session_state:
        st.session_state["loaded"] = False

    col_load, col_reset = st.columns(2)
    with col_load:
        st.button("Charger", key="load_btn", on_click=lambda: st.session_state.update(loaded=True))
    with col_reset:
        st.button("Réinitialiser", key="reset_btn", on_click=lambda: st.session_state.update(loaded=False))

    st.divider()
    page = st.radio(
        "Pages",
        [
            "Aperçu",
            "Tours & Chronos",
            "Télémétrie",
            "Pneus & Stratégie",
            "Arrêts aux stands",
            "Météo",
            "Classements",         # <- nouvelle page
            "Export & Données",
        ],
    )

# Si pas chargé, message
if not st.session_state.get("loaded"):
    st.info("Sélectionnez une saison, un Grand Prix et un type de session, puis cliquez **Charger** les données.")
    st.stop()

# Chargement session
try:
    data = load_session_data(year, event_name, session_type)
    sess_name = data['name']
    laps = data['laps']
    drivers = data['drivers']
    weather = data['weather']
    results = data['results']
    session_key = f"{year}-{event_name}-{session_type}"
    st.success(f"Session {sess_name} chargée ✅")
except Exception as e:
    st.info("Données indisponibles pour cette sélection (connexion, calendrier ou session non disponible).")
    with st.expander("Détails techniques (debug)"):
        st.write(e)
    st.stop()

# Sélecteurs de pilotes dans la SIDEBAR (après chargement)
with st.sidebar:
    st.divider()
    st.subheader("Pilotes")
    if drivers:
        driver_1 = st.selectbox("Pilote 1", drivers, key="drv1_sidebar")
        driver_2 = st.selectbox("Pilote 2 (optionnel)", [""] + drivers, key="drv2_sidebar")
        if driver_2 and driver_2 == driver_1:
            st.warning("Veuillez choisir deux pilotes différents.")
            st.session_state["drv2_sidebar"] = ""
    else:
        st.caption("Aucun pilote disponible")

# Sync des sélections pour le corps de page
driver_1 = st.session_state.get("drv1_sidebar", drivers[0] if drivers else "")
driver_2 = st.session_state.get("drv2_sidebar", "") or ""
if driver_2 == driver_1:
    driver_2 = ""


# Helper: classement de session (course ou autre)
def session_classification(laps_df: pd.DataFrame, results_df: pd.DataFrame, sess_type: str) -> pd.DataFrame:
    """Retourne un classement pour la session courante.
    - Course (R): utilise results si disponible (Position).
    - Autres (FP/Q): meilleur tour par pilote (LapTime minimal).
    """
    if sess_type == 'R' and not results_df.empty and 'Position' in results_df:
        cols = [c for c in ["Position","Abbreviation","DriverNumber","TeamName","TeamColor","Points","Status","Time","FastestLapTime"] if c in results_df.columns]
        df = results_df[cols].copy()
        # Formatage de temps si présents
        for c in ["Time","FastestLapTime"]:
            if c in df.columns:
                try:
                    df[c] = df[c].apply(fmt_timedelta)
                except Exception:
                    pass
        return df.sort_values('Position').reset_index(drop=True)

    # Sinon: meilleur tour par pilote
    if 'Driver' not in laps_df or 'LapTime' not in laps_df:
        return pd.DataFrame()
    tmp = (laps_df.dropna(subset=['Driver','LapTime'])
                  .groupby('Driver', as_index=False)
                  .agg(BestLapTime=('LapTime','min'),
                       BestLapNo=('LapNumber','min')))
    tmp['BestLapStr'] = tmp['BestLapTime'].apply(fmt_timedelta)
    # Ajouter Team si dispo
    if 'Team' in laps_df.columns:
        team_map = laps_df.dropna(subset=['Driver']).drop_duplicates('Driver').set_index('Driver')['Team'].to_dict()
        tmp['Team'] = tmp['Driver'].map(team_map)
    # Ordonner par meilleur temps
    tmp = tmp.sort_values('BestLapTime').reset_index(drop=True)
    tmp['Position'] = tmp.index + 1
    # Couleur d'équipe (facultatif, si on souhaite l'afficher ensuite)
    return tmp[['Position','Driver','Team','BestLapNo','BestLapStr'] if 'Team' in tmp.columns else ['Position','Driver','BestLapNo','BestLapStr']]

# =========================
# PAGES
# =========================
if page == "Aperçu":
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    total_laps = int(laps['LapNumber'].max()) if not laps.empty else 0
    with c1:
        st.metric("Tours totaux", f"{total_laps}")
    with c2:
        st.metric("Pilotes", f"{len(drivers)}")
    with c3:
        st.metric("Type", session_type)
    with c4:
        st.metric("Événement", event_name)

    # Top 10 meilleurs tours
    st.subheader("Chronos – Top 10 meilleurs tours")
    if not laps.empty and 'LapTime' in laps:
        top = (laps.sort_values('LapTime')
                    .loc[laps['LapTime'].notna(),
                         ['Driver','LapNumber','LapTime','LapSeconds','Compound','Stint']]
                    .head(10))
        top['LapTimeStr'] = top['LapTime'].apply(fmt_timedelta)
        st.dataframe(top[['Driver','LapNumber','LapTimeStr','Compound','Stint']], use_container_width=True)
    else:
        st.info("Pas de données de tours.")

    # Répartition des pneus
    st.subheader("Répartition des composés pneus")
    if 'Compound' in laps:
        comp = (laps.dropna(subset=['Compound'])
                    .groupby(['Driver','Compound']).size()
                    .reset_index(name='Tours'))
        fig = px.bar(comp, x='Driver', y='Tours', color='Compound', barmode='stack')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas d'information pneus disponible.")

    # Résultats de course
    st.subheader("Résultats de la course")
    if not results.empty:
        cols = [c for c in ["Position","Abbreviation","DriverNumber","TeamName","Points","Status","Time","FastestLapTime"] if c in results.columns]
        res = results[cols].copy()

        # Formats de temps
        if "Time" in res.columns:
            try:
                res["Time"] = res["Time"].apply(fmt_timedelta)
            except Exception:
                pass
        if "FastestLapTime" in res.columns:
            try:
                res["FastestLapTime"] = res["FastestLapTime"].apply(fmt_timedelta)
            except Exception:
                pass

        st.markdown("Résultats officiels **(si disponibles)**")
        st.dataframe(res, use_container_width=True)
    else:
        st.info("Résultats non disponibles pour cette session.")

    # Meilleur tour de la session
    st.subheader("Meilleur tour de la session")
    if 'LapTime' in laps and laps['LapTime'].notna().any():
        best_idx = laps['LapTime'].idxmin()
        best_row = laps.loc[best_idx]
        bcol1, bcol2, bcol3 = st.columns(3)
        with bcol1:
            st.metric("Pilote", str(best_row.get('Driver', '')))
        with bcol2:
            st.metric("Tour", int(best_row.get('LapNumber', 0)))
        with bcol3:
            st.metric("Temps", fmt_timedelta(best_row.get('LapTime')))
    else:
        st.info("Meilleur tour indisponible.")

elif page == "Tours & Chronos":
    st.subheader("Évolution des temps au tour")
    subset = laps[laps['Driver'].isin([d for d in [driver_1, driver_2] if d])].copy()
    if not subset.empty and subset['LapSeconds'].notna().any():
        fig = px.line(
            subset,
            x='LapNumber', y='LapSeconds', color='Driver',
            labels={'LapSeconds':'Temps (s)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Données de tours insuffisantes.")

    st.subheader("Distribution des temps (histogramme)")
    if not subset.empty and subset['LapSeconds'].notna().any():
        fig_h = px.histogram(subset, x='LapSeconds', color='Driver', nbins=30,
                             labels={'LapSeconds':'Temps (s)'}, marginal='box')
        st.plotly_chart(fig_h, use_container_width=True)

    st.subheader("Table des tours (filtrable)")
    display_cols = ['Driver','LapNumber','LapTime','LapSeconds','Compound','Stint','IsPersonalBest','PitOutTime','PitInTime']
    table = subset[[c for c in display_cols if c in subset.columns]].copy()
    if 'LapTime' in table:
        table['LapTime'] = table['LapTime'].apply(fmt_timedelta)
    if not table.empty:
        st.dataframe(table, use_container_width=True)
        st.download_button(
            "Télécharger CSV",
            data=table.to_csv(index=False).encode('utf-8'),
            file_name=f"laps_{year}_{event_name}_{session_type}.csv",
            mime="text/csv",
        )

elif page == "Télémétrie":
    st.subheader("Vitesse sur le tour le plus rapide")
    try:
        d1_fast, tel_1 = get_fastest_lap_and_tel(f"{year}-{event_name}-{session_type}", laps, driver_1)
        fig = px.line(tel_1, x='Distance', y='Speed', title=f"Tour le plus rapide – {driver_1}")
        if driver_2:
            d2_fast, tel_2 = get_fastest_lap_and_tel(f"{year}-{event_name}-{session_type}", laps, driver_2)
            fig.add_scatter(x=tel_2['Distance'], y=tel_2['Speed'], mode='lines', name=driver_2)
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.metric(f"Meilleur tour {driver_1}", fmt_timedelta(d1_fast['LapTime']))
        if driver_2:
            with c2:
                st.metric(f"Meilleur tour {driver_2}", fmt_timedelta(d2_fast['LapTime']))
    except Exception as e:
        st.info("Télémétrie indisponible pour cette session/pilote.")
        with st.expander("Détails techniques (debug)"):
            st.write(e)

elif page == "Pneus & Stratégie":
    st.subheader("Stints par pilote")
    if {'Stint','Compound','LapNumber'}.issubset(laps.columns):
        stint_ranges = (laps.dropna(subset=['Stint'])
                            .groupby(['Driver','Stint'])
                            .agg(StartLap=('LapNumber','min'), EndLap=('LapNumber','max'),
                                 Compound=('Compound', 'last'))
                            .reset_index())
        st.dataframe(stint_ranges, use_container_width=True)

        st.subheader("Performance moyenne par stint (temps moyen)")
        perf = (laps.dropna(subset=['LapSeconds','Stint'])
                    .groupby(['Driver','Stint','Compound'])['LapSeconds']
                    .mean().reset_index(name='AvgLapSec'))
        fig = px.bar(perf, x='Driver', y='AvgLapSec', color='Compound', barmode='group', facet_row='Stint',
                     labels={'AvgLapSec':'Temps moyen (s)'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Les informations de stints/pneus ne sont pas disponibles pour cette session.")

elif page == "Arrêts aux stands":
    st.subheader("Arrêts détectés")
    if 'PitInTime' in laps or 'PitOutTime' in laps or 'PitStop' in laps:
        pits = laps.copy()
        cols = [c for c in ['Driver','LapNumber','PitInTime','PitOutTime','PitStop','Compound'] if c in pits.columns]
        pits = pits[cols]
        mask = False
        if 'PitInTime' in pits:  mask = mask | pits['PitInTime'].notna()
        if 'PitOutTime' in pits: mask = mask | pits['PitOutTime'].notna()
        if 'PitStop' in pits:    mask = mask | pits['PitStop'].fillna(0).astype(int) > 0
        pits = pits[mask]
        for c in ['PitInTime','PitOutTime']:
            if c in pits:
                pits[c] = pits[c].apply(fmt_timedelta)
        st.dataframe(pits, use_container_width=True)
    else:
        st.info("Aucune donnée d'arrêt aux stands disponible.")

elif page == "Météo":
    st.subheader("Données météo de la session")
    if not weather.empty:
        st.dataframe(weather, use_container_width=True)
        if 'AirTemp' in weather and ('SessionTimeSec' in weather or 'Time' in weather):
            fig_t = px.line(weather, x='SessionTimeSec' if 'SessionTimeSec' in weather else 'Time', y='AirTemp',
                            labels={'AirTemp':'Température air (°C)'}, title="Température de l'air")
            st.plotly_chart(fig_t, use_container_width=True)
        if 'TrackTemp' in weather and ('SessionTimeSec' in weather or 'Time' in weather):
            fig_tt = px.line(weather, x='SessionTimeSec' if 'SessionTimeSec' in weather else 'Time', y='TrackTemp',
                             labels={'TrackTemp':'Température piste (°C)'}, title="Température de la piste")
            st.plotly_chart(fig_tt, use_container_width=True)
        if 'WindSpeed' in weather and ('SessionTimeSec' in weather or 'Time' in weather):
            fig_w = px.line(weather, x='SessionTimeSec' if 'SessionTimeSec' in weather else 'Time', y='WindSpeed',
                            labels={'WindSpeed':'Vent (m/s)'}, title="Vitesse du vent")
            st.plotly_chart(fig_w, use_container_width=True)
    else:
        st.info("Météo indisponible pour cette session.")

elif page == "Classements":
    t1, t2 = st.tabs(["Classement session", "Championnat"])

    with t1:
        st.subheader(f"Classement – {session_type}")
        cls = session_classification(laps, results, session_type)
        if not cls.empty:
            st.dataframe(cls, use_container_width=True)
        else:
            st.info("Classement indisponible pour cette session.")

    with t2:
        ctab1, ctab2 = st.tabs(["Pilotes", "Constructeurs"])
        with ctab1:
            st.subheader("Championnat Pilotes (cumul jusqu'à l'épreuve sélectionnée)")
            with st.spinner("Calcul des points cumulés pilotes..."):
                standings = compute_driver_standings(year, event_name)
            if not standings.empty:
                st.dataframe(standings, use_container_width=True)
            else:
                st.info("Classement pilotes indisponible (données incomplètes ou accès réseau).")
        with ctab2:
            st.subheader("Championnat Constructeurs (cumul jusqu'à l'épreuve sélectionnée)")
            with st.spinner("Calcul des points cumulés constructeurs..."):
                cstand = compute_constructor_standings(year, event_name)
            if not cstand.empty:
                st.dataframe(cstand, use_container_width=True)
            else:
                st.info("Classement constructeurs indisponible (données incomplètes ou accès réseau).")

elif page == "Export & Données":
    st.subheader("Exports rapides")
    if not laps.empty:
        csv = laps.to_csv(index=False).encode('utf-8')
        st.download_button("Télécharger tous les tours (CSV)", data=csv,
                           file_name=f"laps_full_{year}_{event_name}_{session_type}.csv", mime="text/csv")
    if not weather.empty:
        csvw = weather.to_csv(index=False).encode('utf-8')
        st.download_button("Télécharger météo (CSV)", data=csvw,
                           file_name=f"weather_{year}_{event_name}_{session_type}.csv", mime="text/csv")
    if not results.empty:
        csvr = results.to_csv(index=False).encode('utf-8')
        st.download_button("Télécharger résultats (CSV)", data=csvr,
                           file_name=f"results_{year}_{event_name}_{session_type}.csv", mime="text/csv")

    st.info(
        """
        💡 **Astuce maintenance**
        - Navigation via la sidebar (non repliable).
        - Caches sur les chargements (session, télémétrie) pour de meilleures performances.
        - Formats de temps normalisés (secondes + affichage mm:ss.ms).
        - Données exportables pour analyse externe.
        """
    )