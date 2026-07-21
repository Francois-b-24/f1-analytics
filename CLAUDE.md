# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Dashboard Streamlit d'analyse de données de Formule 1, déployé sur Streamlit
Community Cloud : <https://f1-fastanalytics.streamlit.app>.

## Commandes

```bash
# Lancer l'application
streamlit run Home.py

# Tests — les fichiers analytics/adaptateurs/figures/utils sont 100 % hors ligne
pytest tests/ -v
pytest tests/ -v --ignore=tests/test_data_smoke.py   # exclut le seul test réseau
pytest tests/test_adaptateurs.py::test_construire_tours_colonnes_et_valeurs -v

# Lint — bloquant en CI, doit rester clean
ruff check .
ruff check . --fix

# Installation
uv sync                          # ou : pip install -r requirements.txt
```

`pyproject.toml` fixe `pythonpath = ["."]` : les tests importent `from src...`
sans dépendre du répertoire courant.

## Architecture

### Le contrat central

Les 10 pages consomment **une seule fonction**, `chargement_session(annee, course, sess_type)`
(`src/data.py`), qui renvoie un dict au contrat stable :

```
{nom, tours, pilotes, meteo, resultats, tel_par_pilote, best_laps, session_key, session}
```

C'est l'invariant structurant du projet : **changer de source de données se fait
derrière ce contrat**, sans toucher aux pages ni à `src/analytics.py`. La
migration de FastF1 vers OpenF1 a été menée ainsi.

### Chaîne de données

```
src/openf1.py       Client HTTP — tous les appels réseau passent ici
      ↓
src/adaptateurs.py  Conversion OpenF1 → DataFrames (fonctions pures, testables hors ligne)
      ↓
src/data.py         chargement_session(), classements, figures matplotlib
      ↓
pages/*.py          Consomment le dict, ne connaissent pas la source
```

`src/analytics.py` ne dépend ni de Streamlit ni du réseau : pandas/numpy
uniquement, d'où sa testabilité complète hors ligne.

### Source de données : OpenF1, pas FastF1

L'API Live Timing officielle (`livetiming.formula1.com`) est **inaccessible
depuis Streamlit Cloud** (IP de datacenter refusées) : aucune session ne se
chargeait en production, y compris des courses de 2024. Le miroir officiel de
FastF1 répond 404.

Conséquences à connaître :

- **Couverture 2023+** uniquement — OpenF1 ne publie rien avant. Le sélecteur
  d'années part de `openf1.PREMIERE_SAISON`.
- **FastF1 reste une dépendance**, mais uniquement pour **Ergast** (classements
  championnat, `src/data.py`) et son cache disque. Ne pas réintroduire d'appel
  à `fastf1.get_session()` ou `get_event_schedule()` : ils passent par l'API
  bloquée.
- **Quota OpenF1 (HTTP 429)** : le client gère le `retry-after`. La télémétrie
  est récupérée **en séquentiel espacé**, pas en parallèle — mesuré, 4 requêtes
  simultanées saturent le quota et ne ramènent que 17 pilotes sur 22, contre 21
  en séquentiel.
- **Filtrage temporel obligatoire** pour `car_data` : ~5,5 Mo par pilote sans
  filtre, ~90 Ko sur la fenêtre d'un tour.
- Les libellés de Grand Prix incluent le lieu (`"United States Grand Prix (Austin)"`)
  car une saison compte jusqu'à trois GP dans le même pays.

### Mémoire

Contrainte forte : Streamlit Cloud plafonne à ~1 Go. Une session FastF1 pesait
~595 Mo — deux en cache faisaient tuer le processus. Avec OpenF1 : ~200 Mo.
`_chargement_dataframes` est plafonné à `max_entries=2` volontairement ; son
paramètre `_v` invalide le cache à chaque changement de schéma.

### Couleurs

`src/theme.py` est la **source de vérité des couleurs**, y compris pour les
figures matplotlib de `src/data.py` (ne jamais y recoder une couleur en dur :
un thème clair laisserait des graphiques noirs). `appliquer_theme_plotly()` est
appelée par `configure_page()`, donc toutes les figures Plotly héritent du thème
sans modification page par page.

Les palettes ne se choisissent pas à l'œil : elles sont validées (bande de
luminosité, plancher de chroma, séparation daltonisme, contraste sur la
surface). Le thème est **clair** (`#f7f8fa`) et les valeurs d'un thème sombre
n'y sont pas transposables telles quelles. Trois couches doivent rester
cohérentes : `src/theme.py`, `f1_theme.css` (bloc `:root`) et
`.streamlit/config.toml`.

### Contraintes Streamlit

- `st.set_page_config()` doit précéder tout autre appel `st.*` : d'où
  l'ignorance de `E402` sur `Home.py` et `pages/*.py` dans `pyproject.toml`.
- Chaque page appelle `selections_courantes(required=True)` (`src/ui.py`), qui
  arrête la page si aucune session n'est chargée.
- Le contenu d'un `st.dataframe` est rendu en canvas : `inner_text` ne le voit
  pas — ne pas conclure à une page vide sur cette seule base lors d'un test
  automatisé.

## Données d'énergie 2026

La F1 **ne publie aucune donnée d'énergie** (état de charge ERS, déploiement
MGU-K, aéro active) — confirmé par le mainteneur de FastF1
([discussion #861](https://github.com/theOehrly/Fast-F1/discussions/861)).

La page `10_Energie_&_2026.py` ne mesure donc rien : elle **dérive** des
indicateurs à partir des seuls canaux publiés (freinage comme proxy de
récupération, pleine charge comme proxy de déploiement). Toute évolution de
cette page doit conserver l'affichage explicite de ce statut d'estimation.

Le canal `DRS` est volontairement écarté des indicateurs : vérifié sur données
réelles, il ne contient que des `0` en 2026 comme en 2024.

## Déploiement

Streamlit Cloud lit `requirements.txt` (versions épinglées), `runtime.txt` et
`.streamlit/config.toml`. Push sur `master` → rebuild automatique.

Point d'attention constaté : **la CI qui échoue bloque le redéploiement**. Un
lint rouge suffit à figer la production sur une version antérieure. Si la prod
sert un ancien code, vérifier l'état de la CI avant tout autre diagnostic.

Le workflow `wake-streamlit.yml` sonde l'app toutes les 6 h (Puppeteer) et
**échoue avec un code non nul** si une app reste inaccessible — un échec
silencieux avait masqué une panne durable.
