# 🏎️ F1 Analytics Dashboard

Application **Streamlit** basée sur **FastF1** pour analyser les données de Formule 1 : chronos, télémétrie, météo, pneus, arrêts aux stands, etc.

---

## 🚀 Fonctionnalités

- Analyse des **temps en au tours** et de la télémétrie. Avec la possibilité d'effectuer une comparaison entre 2 pilotes pour une même session.
- Données **pneus et stratégies**
- **Météo** : température air/piste, vent
- **Classements** pilotes et constructeurs
- Possibilité d'exporter des données au format **CSV**
- Menu et filtres interactifs

---

## 📁 Structure du projet

```bash
f1-analytics/
├─ Home.py                # Page d’accueil principale
├─ scr/                 # Fonctions internes (config, data, ui, utils)
├─ pages/                # Pages Streamlit (Tours, Télémétrie, météo, etc.)
├─ requirements.txt     #Pour déploiement en streamlitcloud
├─ pyproject.toml  #Configuration de l'env et des dépendances
├─ Dockerfile
└─ README.md
```
---

## ⚙️ Installation locale

1️⃣ **Cloner le dépôt**
```bash
git clone https://github.com/<ton-utilisateur>/f1-analytics.git
cd f1-analytics
```

2️⃣ Installer les dépendances
```bash
uv sync
```
ou avec poetry :

```bash
poetry install
```

3️⃣ Lancer l’application
```bash
streamlit Home.py
```

🧰 Technologies

- Python 
- Streamlit
- FastF1
- Plotly
- Docker

✨ Projet réalisé par BOUSSENGUI François,
Passionné de data science et de Formule 1 🏁.
