# 🏎️ F1 Analytics Dashboard

**Production** : [https://f1-fastanalytics.streamlit.app](https://f1-fastanalytics.streamlit.app)

Application **Streamlit** basée sur **[FastF1](https://docs.fastf1.dev/)** pour explorer interactivement les données d'un week-end de Grand Prix : chronos, télémétrie, pneus & stratégies, météo, arrêts aux stands, classements, cartographie circuit, secteurs.

---

## 🚀 Fonctionnalités

- **Chronos & télémétrie** — meilleur tour par pilote, vitesse / rapports le long du tracé, comparaison 2 pilotes
- **Pneus & stratégies** — composés utilisés, dégradation par stint, matrice de dégradation
- **Météo** — température air/piste, vent, humidité au fil de la session
- **Classements** — pilotes & constructeurs cumulés jusqu'à un Grand Prix donné (via Ergast)
- **Pitstops** — durée et timing des arrêts aux stands
- **Cartographie circuit** — carte de vitesse, rapports engagés, numérotation des virages
- **Secteurs** — décomposition par secteurs (S1/S2/S3)
- **Export CSV** des données chargées

---

## 📁 Architecture

```
f1-analytics/
├─ Home.py                       # Point d'entrée Streamlit (overview + KPIs)
├─ src/                          # Modules internes
│  ├─ config.py                  # Setup pages, cache FastF1, logging, Sentry
│  ├─ data.py                    # Chargement session, classements, figures
│  ├─ ui.py                      # Sélecteurs (saison, GP, type session, pilotes)
│  ├─ analytics.py               # Calculs (dégradation, delta, secteurs)
│  └─ utils.py                   # Helpers (formatage timedelta, secs)
├─ pages/                        # Pages Streamlit (multi-page app)
│  ├─ 1_Chronos_&_Télémetries.py
│  ├─ 2_Performances.py
│  ├─ 3_Pneus_&_strategies.py
│  ├─ 4_Meteo.py
│  ├─ 5_Classements.py
│  ├─ 6_Pitstops.py
│  ├─ 7_Cartographie.py
│  ├─ 8_Exports_de_donnees.py
│  └─ 9_Secteurs.py
├─ tests/                        # pytest (smoke + analytics)
├─ probe-action/                 # GitHub Action keep-alive (Puppeteer)
├─ .github/workflows/            # CI + probe
├─ .streamlit/config.toml        # Conf Streamlit (theme, logger, server)
├─ requirements.txt              # Déploiement Streamlit Cloud (versions épinglées)
├─ runtime.txt                   # Version Python pour Streamlit Cloud
├─ pyproject.toml + uv.lock      # Env de dev (uv)
└─ f1_theme.css                  # Thème CSS F1
```

---

## ⚙️ Développement local

### Prérequis
- Python 3.11
- [uv](https://github.com/astral-sh/uv) recommandé (ou pip)

### Installation

```bash
git clone https://github.com/<ton-utilisateur>/f1-analytics.git
cd f1-analytics

# Avec uv (recommandé)
uv sync

# Ou avec pip
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Lancer l'app

```bash
streamlit run Home.py
```

### Lancer les tests

```bash
pytest tests/ -v
```

---

## ☁️ Déploiement Streamlit Community Cloud

L'app est déployée sur [share.streamlit.io](https://share.streamlit.io). Streamlit Cloud lit :

- **`requirements.txt`** — versions épinglées (clé pour éviter les régressions amont)
- **`runtime.txt`** — `python-3.11`
- **`.streamlit/config.toml`** — theme + logger + server config
- **Secrets** (panel Streamlit Cloud → Settings → Secrets) :
  ```toml
  SENTRY_DSN = "https://...@sentry.io/..."   # optionnel
  ```

Après un push sur `master`, Streamlit Cloud rebuild automatiquement. Suivre les logs : **Manage app → Logs**.

---

## 🔧 Variables d'environnement

- `FASTF1_CACHE` — chemin du cache FastF1 (défaut : `/tmp/fastf1_cache`)
- `LOG_LEVEL` — `INFO`, `DEBUG`, `WARNING` (défaut `INFO`)
- `SENTRY_DSN` — DSN Sentry (optionnel ; aussi lisible via `st.secrets`)
- `ENV` — `prod` / `staging` (envoyé à Sentry)

---

## 💾 Cache FastF1

FastF1 met en cache toutes les requêtes API (laps, télémétrie, météo) dans un dossier local. La résolution du chemin suit cet ordre :

1. Variable d'environnement `FASTF1_CACHE` si définie
2. `/tmp/fastf1_cache` sinon (cache éphémère, survit à la session Streamlit Cloud)

Le dossier `cache/` du repo est **dans `.gitignore`** — ne pas le committer (lourd + risque de schéma incompatible avec une nouvelle version de FastF1).

**Purger le cache** (en cas de schéma périmé) :
```bash
rm -rf $FASTF1_CACHE   # ou /tmp/fastf1_cache
```

---

## 🔭 Observabilité

### Logs

Format centralisé via `src.config.logger` :
```
2025-10-15 12:34:56 [INFO] f1_analytics.data:75 — Chargement session 2024 / Australian Grand Prix / R
```

Niveau pilotable par `LOG_LEVEL` (env var).

### Sentry (optionnel mais recommandé en prod)

Ajouter `SENTRY_DSN` aux secrets Streamlit Cloud → toute exception non rattrapée est automatiquement remontée. Initialisation idempotente dans [`src/config.py`](src/config.py).

### Probe keep-alive

Le workflow [`.github/workflows/probe.yml`](.github/workflows/) ping l'app toutes les 6 h via [`probe-action/probe.js`](probe-action/probe.js) (Puppeteer) pour éviter la mise en veille Streamlit Cloud.

---

## 🛠️ Troubleshooting

| Symptôme | Cause probable | Solution |
|---|---|---|
| « Session indisponible » sur prod | Session non encore disputée ou résultats non publiés | Choisir une saison antérieure ou un GP terminé |
| Crash silencieux après quelques chargements | OOM Streamlit Cloud (≈1 GB) | `max_entries=4` sur `chargement_session` borne la conso. Redémarrer l'app via le panel. |
| Erreur au premier `load()` après update FastF1 | Schéma du cache SQLite incompatible | Purger `$FASTF1_CACHE` |
| Calendrier vide dans le sélecteur | API FastF1 / Ergast temporairement KO | Réessayer dans quelques minutes |
| `ImportError` sur sentry_sdk | Pas dans `requirements.txt` | Vérifier que la dépendance est bien listée et redéployer |

---

## 🧪 CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) exécute à chaque push/PR :
- `ruff check` (non bloquant pour l'instant)
- `pytest tests/`
- Smoke import de `Home.py`

---

## 🧰 Stack

- **Python 3.11**
- **Streamlit 1.50** — UI
- **FastF1 3.6** — données F1 (Live Timing + Ergast)
- **Pandas 2.3 / NumPy 2.2** — manipulation
- **Plotly 6 / Matplotlib 3.9** — visualisations
- **Sentry SDK** — observabilité

---

✨ Projet réalisé par **BOUSSENGUI François**, passionné de data science et de Formule 1 🏁.
