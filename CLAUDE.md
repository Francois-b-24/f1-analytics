# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Dashboard Streamlit d'analyse de données de Formule 1, déployé sur Streamlit
Community Cloud : <https://f1-fastanalytics.streamlit.app>.

## Commandes

```bash
# Lancer l'application
streamlit run streamlit_app.py

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
{nom, tours, pilotes, meteo, resultats, best_laps, session_key, session}
```

C'est l'invariant structurant du projet : **changer de source de données se fait
derrière ce contrat**, sans toucher aux pages ni à `src/analytics.py`. La
migration de FastF1 vers OpenF1 a été menée ainsi.

La **télémétrie n'est pas dans ce dict** : elle est chargée à la demande, pilote
par pilote, via `telemetrie_pilote(data, code)` (ou `tour_rapide_tel`). Charger
les 22 pilotes d'emblée coûtait ~45 s alors que 7 pages sur 10 n'en affichent
aucune ; désormais la session s'ouvre en ~3-4 s et un pilote se charge en ~1 s
(caché par `_telemetrie_pilote_cache`). `best_laps` porte les infos nécessaires
au chargement paresseux (numéro, fenêtre temporelle du meilleur tour).

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
- **Quota OpenF1 (HTTP 429)** : le client gère le `retry-after` (avec jitter).
  Les 7 endpoints de métadonnées sont chargés à **`openf1.REQUETES_SIMULTANEES`
  threads** (3) au chargement de session. Le coût est réseau à ~99 % ; au-delà
  de 3 threads, le quota morderait et annulerait le gain. La télémétrie, elle,
  est chargée à la demande (voir plus haut), donc une requête à la fois.
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

`f1_theme.css` expose une classe de carte réutilisable (`.f1-carte`) et un
bloc `@media (max-width: 900px)` qui resserre les métriques sur petit écran.
La police est la **pile système** : `'Inter'` était nommée sans jamais être
chargée (ni `@import` ni `@font-face`), donc tous les postes y retombaient
déjà ; l'importer coûterait une requête bloquante au premier rendu.

Les palettes ne se choisissent pas à l'œil : elles sont validées (bande de
luminosité, plancher de chroma, séparation daltonisme, contraste sur la
surface). Le thème est **clair** (`#f7f8fa`) et les valeurs d'un thème sombre
n'y sont pas transposables telles quelles. Trois couches doivent rester
cohérentes : `src/theme.py`, `f1_theme.css` (bloc `:root`) et
`.streamlit/config.toml`.

### Contraintes Streamlit

- La navigation passe par `st.navigation`/`st.Page` : `streamlit_app.py` est le
  routeur et **le seul** à appeler `st.set_page_config()`. Les pages de `pages/`
  ne le font plus — un second appel ne lève pas (il est additif, le dernier
  gagne) mais écraserait silencieusement le titre d'onglet et le menu « About »
  du routeur. `tests/test_navigation.py` garde ce contrat.
- Le registre des pages est `src/navigation.py` : libellés, icônes et `url_path`
  y sont déclarés. `url_path` est **épinglé** pour qu'un renommage de fichier ne
  casse ni les liens ni les favoris.
- Le sélecteur de session (`selecteurs_session_sidebar`, `src/ui.py`) est rendu
  par le routeur dans la barre latérale, donc disponible sur toutes les pages.
  Il est décoré `@st.fragment` : ne pas y appeler `st.sidebar` (Streamlit
  l'interdit depuis un fragment — c'est l'appelant qui ouvre le contexte), et
  tout `st.rerun()` y doit porter `scope="app"`, sinon seul le fragment est
  relancé.
- Piège figé par les tests : un `st.selectbox` recevant **à la fois** `key=` et
  un `index=` dérivé de l'état validé boucle sur lui-même — au rerun, l'index
  est recalculé depuis l'ancienne valeur et écrase le choix de l'utilisateur.
  D'où `_index_initial()`, qui ne fournit `index` qu'au premier rendu.
- Chaque page appelle `selections_courantes(required=True)` (`src/ui.py`), qui
  arrête la page si aucune session n'est chargée.
- Chaque page commence par `entete_page("<module>")` (`src/ui.py`) : titre,
  accroche et « Comment lire cette page ». Les textes vivent dans
  `src/pedagogie.py`, pas dans les pages — c'est du contenu éditorial, relu
  souvent, et `tests/test_pedagogie.py` vérifie la bijection page ↔ texte.
  Seul `pages/accueil.py` garde un titre en HTML stylé (identité visuelle).
- `use_container_width` est **déprécié** (retrait annoncé après le 31/12/2025) :
  utiliser `width="stretch"` ou `width="content"`.
  `tests/test_coherence_pages.py` l'interdit.
- Les tableaux passent par `st.dataframe`, jamais par
  `st.write(df.to_html(...), unsafe_allow_html=True)` : le HTML brut prive du
  tri, du redimensionnement et du style `.stDataFrame`.
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

**Le point d'entrée est configuré hors du dépôt.** Streamlit Cloud stocke le
« Main file path » dans les réglages de l'app : renommer le fichier d'entrée
casse la production (« Error running app ») sans que lint, tests ni CI ne
rougissent. C'est arrivé en renommant `Home.py` en `streamlit_app.py`.

`Home.py` subsiste donc comme alias délégant à `streamlit_app.py`, et
`tests/test_points_entree.py` vérifie que **les deux** démarrent réellement
(pas seulement qu'ils s'importent). Pour supprimer l'alias : changer le réglage
côté Streamlit Cloud, vérifier le démarrage, puis retirer le fichier *et* son
entrée dans `POINTS_ENTREE`.

Corollaire : `st.Page` résout les chemins relatifs depuis le **script d'entrée**,
pas depuis le module déclarant. `src/navigation.py` les ancre donc sur la racine
du projet (`_RACINE`), sinon un point d'entrée placé ailleurs lève
« Unable to create Page ».

Streamlit Cloud lit `requirements.txt` (versions épinglées), `runtime.txt` et
`.streamlit/config.toml`. Push sur `master` → rebuild automatique.

Point d'attention constaté : **la CI qui échoue bloque le redéploiement**. Un
lint rouge suffit à figer la production sur une version antérieure. Si la prod
sert un ancien code, vérifier l'état de la CI avant tout autre diagnostic.

Le workflow `wake-streamlit.yml` sonde l'app toutes les 6 h (Puppeteer) et
**échoue avec un code non nul** si une app reste inaccessible — un échec
silencieux avait masqué une panne durable.
