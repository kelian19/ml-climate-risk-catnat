# Sécheresse CatNat : fréquence annuelle de reconnaissance par commune

Modèle de **fréquence** du péril sécheresse (retrait-gonflement des argiles) au sens du régime CatNat : pour chaque commune de France métropolitaine et chaque année, probabilité qu'un arrêté de reconnaissance porte sur un événement débutant cette année-là, à partir de l'humidité des sols Météo-France et de l'exposition aux argiles.

Le projet d'origine (notebooks archivés dans [`archive/notebooks/`](archive/notebooks/)) prédisait le SWI lui-même, avec le SWI de la veille en variable explicative et des découpages aléatoires. Ses défauts sont décrits dans [AUDIT.md](AUDIT.md). Cette version repart des sources publiques et pose la question actuarielle : **quelle est la fréquence de reconnaissance, et le modèle est-il calibré en nombre de communes touchées par an ?**

## Données (publiques, téléchargées et vérifiées par empreinte)

| Source | Usage |
|---|---|
| Météo-France, SIM2 mensuelle Safran-Isba 2000–2025 (maille ≈ 8 km) | SWI, SSWI3, SSWI12 |
| Météo-France, points de grille `SHP_SIM_FRANCE` | Rattachement commune → maille (centre de commune, distance médiane 3 km, max 12,7 km) |
| data.gouv.fr, arrêtés CatNat par commune (GASPAR) | Variable à expliquer : périls « Sécheresse » et « Retrait-gonflement des argiles » |
| SDES, exposition RGA par EPCI | Part de surface en aléa moyen et fort |
| geo.api.gouv.fr, communes | Centre, population, surface, EPCI |

`python -m pipeline.download` télécharge ≈ 155 Mo dans `data/raw/` (non versionné) et contrôle les empreintes de [`data/manifest.json`](data/manifest.json). Détail : [data_catalog.md](data_catalog.md).

## Méthode

- **Variable à expliquer.** `y = 1` si la commune a au moins un arrêté sécheresse pour un événement débutant l'année t. Grille complète commune × année (34 746 communes, 2006–2022, 590 682 lignes, fréquence moyenne 4,3 %).
- **Censure à droite.** Un arrêté est publié de quelques mois à plusieurs années après la fin de l'événement (médiane 0,5 à 4 ans selon l'année, jusqu'à 9 ans). La dernière année retenue est calculée : 2022 est mûre à la date de coupure du fichier (9 juillet 2025), 2023 ne l'est pas ([figure](reports/figures/retard_publication.png)).
- **Indicateurs météo sans information future.** Anomalies standardisées du SWI (été, automne, minimum mensuel, été précédent) calculées avec une climatologie **des seules années antérieures**, plus SSWI3 de septembre et SSWI12 de décembre.
- **Exposition.** Parts de surface RGA moyen et fort de l'EPCI, population (log).
- **Historique connu.** Nombre d'années de reconnaissance sur les dix années précédentes, **en ne comptant que les arrêtés déjà publiés au 1er janvier de l'année prédite**.
- **Validation en temps réel.** Pour prédire l'année t, apprentissage sur les années ≤ t − 2 seulement (retard de publication), années de test 2010–2022. Aucun découpage aléatoire.
- **Modèles.** Fréquence constante ; fréquence par commune crédibilisée (Bühlmann simplifié, k = 3) ; régressions logistiques de plus en plus riches ; gradient boosting.

## Résultats mesurés (hors échantillon, 2010–2022)

| Modèle | Log-loss | Gain de log-loss vs constante | Brier | AUC | Communes attendues / observées |
|---|---:|---:|---:|---:|---:|
| Fréquence constante | 0,2264 | 0 % | 0,0514 | 0,638 | 7 738 / 24 106 |
| Fréquence commune crédibilisée | 0,2319 | −2,5 % | 0,0493 | 0,663 | 7 738 / 24 106 |
| GLM météo | 0,2028 | 10,4 % | 0,0496 | 0,804 | 13 153 / 24 106 |
| GLM météo + exposition | 0,1900 | 16,1 % | 0,0460 | 0,850 | 11 365 / 24 106 |
| **GLM complet** (+ historique publié) | **0,1838** | **18,8 %** | 0,0446 | 0,861 | 11 646 / 24 106 |
| GBM complet | 0,1929 | 14,8 % | 0,0435 | 0,861 | 9 801 / 24 106 |

![Observé contre attendu](reports/figures/observe_attendu.png)

**Lecture.**
- Le modèle **classe bien les communes** au sein d'une année (AUC de 0,69 en 2018 à 0,96 selon l'année), et l'humidité des sols est de loin le premier facteur, devant l'exposition aux argiles et l'historique.
- Il **sous-estime fortement le nombre de communes reconnues en 2018–2020** (observé/attendu de 4 à 15) puis retrouve le bon ordre de grandeur en 2021–2022. Ce décalage coïncide avec une forte hausse des reconnaissances à partir de 2018, que les années d'apprentissage antérieures ne contiennent pas : le niveau de reconnaissance n'est pas stationnaire, et la météo seule ne l'explique pas. Une charge de portefeuille fondée sur ce modèle exigerait un recalage annuel du niveau (fréquence de base), à documenter avant tout usage.
- La fréquence par commune sans météo fait **moins bien que la constante** en log-loss : le passé seul ne prédit pas l'année suivante, la sécheresse étant pilotée par le climat de l'année.
- Les coefficients des indicateurs météo sont corrélés entre eux (le SWI d'été a un signe positif une fois le SSWI3 de septembre pris en compte) : ils s'interprètent conjointement, pas un par un.

Détail par année, calibration par décile et coefficients : [reports/RESULTATS.md](reports/RESULTATS.md) et [reports/results.json](reports/results.json).

## Limites

- **Fréquence de reconnaissance, pas de charge** : aucune donnée de sinistres ni de coûts n'est publique à la commune. Le modèle ne fournit ni prime pure ni coût moyen.
- La reconnaissance dépend aussi d'une procédure administrative (demande communale, critères modifiés au cours de la période) que les données météo ne décrivent pas.
- Exposition RGA et population sont des photographies récentes appliquées à toutes les années ; 14 communes sans donnée RGA (indicateur dédié).
- Rattachement à une seule maille par commune (centre), sans pondération par la surface argileuse.

## Utilisation

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt   # Windows : .venv\Scripts\
python -m pipeline.download   # ≈ 155 Mo, une fois
python -m pipeline.run        # table, validation, reports/results.json, figures (quelques minutes)
python -m pytest tests -q     # tests unitaires ; les contrôles sur données réelles s'exécutent si data/raw existe
```

## Organisation

- `catnat/` : lecture des sources, variable à expliquer et maturité, indicateurs, modèles, mesures.
- `pipeline/` : téléchargement vérifié et exécution complète.
- `tests/` : tests unitaires sur données synthétiques (absence de fuite temporelle, historique publié, crédibilité, mesures, formats des sources) et contrôles sur données réelles.
- `reports/` : résultats mesurés et figures.
- `archive/notebooks/` : notebooks d'origine, conservés pour traçabilité, non utilisés.
