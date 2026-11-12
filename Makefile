.DEFAULT_GOAL := help
.PHONY: help install install-dev run lint fmt test test-reseau test-all cov check hooks clean

PY ?= python3

help:  ## Affiche cette aide
	@grep -hE '^[a-z-]+:.*?##' $(MAKEFILE_LIST) \
		| sed 's/:.*##/\t/' \
		| awk -F'\t' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Installe les dépendances d'exécution (versions épinglées)
	$(PY) -m pip install -r requirements.txt

install-dev:  ## Installe aussi l'outillage de développement
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e ".[dev]"

run:  ## Lance l'application
	streamlit run streamlit_app.py

lint:  ## Vérifie le style (bloquant en CI — doit rester clean)
	ruff check .

fmt:  ## Corrige ce qui peut l'être automatiquement
	ruff check --fix .

test:  ## Lance la suite hors ligne (rapide, aucun accès réseau)
	pytest -m "not reseau" -q

test-reseau:  ## Lance uniquement les tests qui interrogent OpenF1
	pytest -m reseau -v

test-all:  ## Lance toute la suite, réseau compris
	pytest -v

cov:  ## Couverture de src/ (hors ligne)
	pytest -m "not reseau" --cov=src --cov-report=term-missing

check: lint test  ## Ce que la CI exige : lint + suite hors ligne
	@echo "OK — lint propre et suite hors ligne verte"

hooks:  ## Installe les hooks pre-commit
	pre-commit install

clean:  ## Supprime les caches locaux
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
