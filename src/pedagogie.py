"""Textes pédagogiques et glossaire — contenu éditorial, sans logique.

Séparé du code à dessein : ces textes sont relus et reformulés souvent, et les
garder hors des pages évite d'y retoucher à chaque correction de formulation.
Une seule source alimente les trois usages : l'en-tête de page, le glossaire
complet et les bulles `help=` des métriques.

Le public visé inclut des lecteurs qui ne suivent pas la F1 : chaque page doit
dire ce qu'on regarde et comment le lire, sans jargon non expliqué.
"""
from __future__ import annotations

# Clé = nom du module de page (sans .py), pour que le lien soit évident.
EXPLICATIONS: dict[str, dict[str, str]] = {
    "accueil": {
        "titre": "Vue d'ensemble du week-end",
        "accroche": (
            "Les chiffres clés de la session choisie : qui a signé le meilleur "
            "tour, combien de tours ont été couverts, quels pneus ont été "
            "utilisés et quel a été le classement final."
        ),
        "lecture": (
            "Commencez par le **meilleur tour** : c'est la référence de vitesse "
            "pure de la session. Le graphique des composés montre la stratégie "
            "pneumatique de chaque pilote — un pilote qui a beaucoup roulé en "
            "tendre a privilégié la performance, au prix de la durabilité."
        ),
    },
    "classements": {
        "titre": "Classements",
        "accroche": (
            "Le classement de la session sélectionnée, et l'état des deux "
            "championnats (pilotes et constructeurs) cumulé jusqu'à cette épreuve."
        ),
        "lecture": (
            "Le classement de session reflète cette séance uniquement. Les "
            "onglets Championnat cumulent les points de toutes les épreuves "
            "disputées jusqu'à celle choisie — utile pour situer une course "
            "dans la saison plutôt que de la lire isolément."
        ),
    },
    "chronos_telemetries": {
        "titre": "Chronos & télémétries",
        "accroche": (
            "L'évolution des temps au tour, et la comparaison détaillée de deux "
            "pilotes sur leur meilleur tour : vitesse, écart cumulé, secteurs."
        ),
        "lecture": (
            "Sur la courbe des temps au tour, les pics correspondent presque "
            "toujours à un passage par les stands ou à une neutralisation. "
            "Le graphique de **delta** montre où un pilote gagne ou perd du "
            "temps sur l'autre : une pente qui monte signifie que le second "
            "perd du terrain à cet endroit du circuit."
        ),
    },
    "secteurs": {
        "titre": "Analyse par secteur",
        "accroche": (
            "Chaque tour est découpé en trois secteurs chronométrés. Comparer "
            "secteur par secteur révèle *où* un pilote est rapide, pas seulement "
            "de combien."
        ),
        "lecture": (
            "Un pilote peut être le plus rapide au tour sans dominer aucun "
            "secteur : la régularité paie. Un écart concentré sur un seul "
            "secteur pointe souvent une différence de réglage — appui "
            "aérodynamique dans les virages, vitesse de pointe en ligne droite."
        ),
    },
    "positions": {
        "titre": "Positions par tour",
        "accroche": (
            "L'évolution de la position de chaque pilote au fil des tours : "
            "le récit de la course en un seul graphique."
        ),
        "lecture": (
            "Les croisements de lignes sont des changements de position. Une "
            "chute brutale puis une remontée progressive est la signature d'un "
            "arrêt aux stands. Les données de position n'existent que pour les "
            "courses, pas pour les essais ni les qualifications."
        ),
    },
    "pneus_strategies": {
        "titre": "Pneus & stratégies",
        "accroche": (
            "Quels pneus, pendant combien de tours, et à quel rythme : la "
            "stratégie pneumatique et la perte de performance qu'elle entraîne."
        ),
        "lecture": (
            "La **dégradation** se lit sur la pente : plus elle monte, plus le "
            "pneu perd de performance à chaque tour. Un pneu tendre est plus "
            "rapide d'emblée mais se dégrade plus vite — tout l'enjeu "
            "stratégique est là."
        ),
    },
    "arrets": {
        "titre": "Arrêts aux stands",
        "accroche": (
            "Quand chaque pilote s'est arrêté, combien de temps, et ce que "
            "cela dit de la stratégie de son équipe."
        ),
        "lecture": (
            "La durée affichée est l'immobilisation, pas la perte totale, qui "
            "inclut aussi le ralentissement dans la voie des stands. Deux "
            "pilotes de la même écurie qui s'arrêtent à des tours différents "
            "appliquent souvent des stratégies délibérément opposées."
        ),
    },
    "meteo": {
        "titre": "Météo",
        "accroche": (
            "Températures de l'air et de la piste, et vitesse du vent au fil "
            "de la session — des conditions qui changent tout au comportement "
            "des pneus."
        ),
        "lecture": (
            "L'écart entre piste et air est la donnée la plus parlante : une "
            "piste très chaude accélère la dégradation des pneus et pousse à "
            "s'arrêter plus tôt. Une piste qui refroidit en fin de journée "
            "redonne au contraire de l'adhérence."
        ),
    },
    "cartographie": {
        "titre": "Cartographie du circuit",
        "accroche": (
            "Le tracé du circuit coloré selon la vitesse et le rapport de "
            "boîte engagé, sur le meilleur tour du pilote choisi."
        ),
        "lecture": (
            "Les zones les plus froides de la carte de vitesse sont les points "
            "de freinage les plus appuyés. La carte des rapports montre le "
            "rythme du circuit : beaucoup de rapports bas signale un tracé "
            "lent et technique."
        ),
    },
    "energie_2026": {
        "titre": "Énergie & 2026",
        "accroche": (
            "Des indicateurs **estimés** d'usage de l'énergie électrique, en "
            "vue de la réglementation 2026 — la F1 ne publiant aucune donnée "
            "d'énergie, ils sont dérivés des canaux disponibles."
        ),
        "lecture": (
            "Ces chiffres ne sont pas des mesures. Le freinage sert "
            "d'approximation à la récupération d'énergie, la pleine charge à "
            "son déploiement. Ils servent à comparer des pilotes entre eux sur "
            "une même session, pas à quantifier une énergie en kilojoules."
        ),
    },
    "exports": {
        "titre": "Exports de données",
        "accroche": (
            "Récupérez les données de la session au format CSV pour les "
            "analyser avec vos propres outils."
        ),
        "lecture": (
            "Les fichiers reprennent exactement les données affichées dans "
            "l'application, sans transformation supplémentaire. Les durées sont "
            "exprimées en secondes pour rester exploitables dans un tableur."
        ),
    },
    "glossaire": {
        "titre": "Glossaire & méthodologie",
        "accroche": (
            "Les termes de la Formule 1 employés dans l'application, et la "
            "provenance des données."
        ),
        "lecture": "",
    },
}


# Vocabulaire réellement utilisé dans l'application. Chaque définition tient en
# une ou deux phrases : c'est une aide de lecture, pas un article.
GLOSSAIRE: dict[str, str] = {
    "Tour rapide": (
        "Le meilleur temps au tour réalisé pendant la session. Sert de "
        "référence de vitesse pure."
    ),
    "Relais (stint)": (
        "Une série de tours consécutifs effectués avec le même train de pneus. "
        "Un relais se termine à l'arrêt aux stands."
    ),
    "Composé": (
        "Le type de gomme du pneu. Du plus tendre au plus dur : tendre (rapide "
        "mais s'use vite), medium, dur (plus lent mais durable)."
    ),
    "Dégradation": (
        "La perte progressive de performance d'un pneu au fil des tours. Se "
        "mesure par l'augmentation du temps au tour à mesure que le pneu vieillit."
    ),
    "Delta": (
        "Un écart de temps. Le « delta cumulé » entre deux pilotes montre, "
        "mètre par mètre, où l'un prend l'avantage sur l'autre."
    ),
    "Secteur": (
        "Chaque tour est divisé en trois portions chronométrées séparément "
        "(S1, S2, S3), ce qui permet de localiser les écarts."
    ),
    "Undercut": (
        "S'arrêter aux stands avant un concurrent pour profiter de pneus neufs "
        "plus rapides et le dépasser pendant qu'il roule encore sur des pneus usés."
    ),
    "Overcut": (
        "L'inverse de l'undercut : rester en piste plus longtemps que son "
        "concurrent, en espérant profiter d'une piste plus dégagée."
    ),
    "Tour personnel (PB)": (
        "Le meilleur tour d'un pilote donné, par opposition au meilleur tour "
        "absolu de la session."
    ),
    "Tour de sortie / rentrée": (
        "Le tour où un pilote quitte les stands (sortie) ou y entre (rentrée). "
        "Ces tours sont plus lents et faussent les moyennes."
    ),
    "ERS": (
        "Système de récupération d'énergie. Récupère l'énergie au freinage pour "
        "la restituer en accélération."
    ),
    "MGU-K": (
        "Le moteur-générateur lié aux roues : il freine pour récupérer de "
        "l'énergie, puis la restitue comme surcroît de puissance."
    ),
    "DRS": (
        "Aileron arrière mobile réduisant la traînée en ligne droite pour "
        "faciliter les dépassements. Son usage est réglementé."
    ),
    "Grille de départ": (
        "L'ordre de départ, déterminé par les qualifications."
    ),
    "Tour chronométré": (
        "Un tour lancé, destiné à établir un temps — par opposition à un tour "
        "de mise en température ou de retour aux stands."
    ),
}


def aide(terme: str) -> str:
    """Définition d'un terme, pour alimenter un `help=` sans dupliquer le texte.

    Retourne une chaîne vide si le terme est inconnu, afin qu'une coquille
    n'affiche pas d'infobulle trompeuse plutôt que de faire échouer la page.
    """
    return GLOSSAIRE.get(terme, "")


def explication(page: str) -> dict[str, str]:
    """Textes d'une page. Repli neutre si la page n'est pas encore documentée."""
    return EXPLICATIONS.get(page, {"titre": page.replace("_", " ").title(),
                                   "accroche": "", "lecture": ""})
