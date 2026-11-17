# Risque climatique (sécheresse) : modélisation du SWI par ML et géostatistique

Copie documentée de [Kelian2909/ml-climate-risk-catnat](https://github.com/Kelian2909/ml-climate-risk-catnat) (historique conservé). Le projet étudie le **Soil Water Index (SWI)** de la grille Safran, indicateur d'humidité des sols lié à la sécheresse et, en aval, au retrait-gonflement des argiles (régime CatNat). **Les notebooks modélisent le SWI, pas des sinistres : aucun lien avec des pertes assurées n'est établi dans ce dépôt.**

## Contenu

| Notebook | Sujet |
|---|---|
| `src/analyse_swi.ipynb` | Analyse exploratoire du SWI France 2000–2019 (~72 millions de points) : distribution, anomalies z-score, saisonnalité, autocorrélation, spectre, clusters KMeans. |
| `src/par1.ipynb` | Exploration et jointure des bases (parquet, GeoPackage), préparation du département 13. |
| `src/random_forest_13.ipynb` | Bouches-du-Rhône : forêt aléatoire contre régression linéaire, avec aléa argiles BRGM. |
| `src/SAR_CAR_KRIGING_NAQ.ipynb` | Nouvelle-Aquitaine : autocorrélation spatiale (Moran), modèles SAR/CAR, krigeage, incertitude. |
| `src/Transfer_NAQ_GE.ipynb` | Transfert d'un modèle appris en NAQ vers le Grand Est, avec prédiction conforme (CQR) et recalibrage géostatistique. |

Métadonnées : [`data_catalog.md`](data_catalog.md) (sources, **encore incomplet**), [`decision_log.md`](decision_log.md), [`environment.yml`](environment.yml).

## État et limites

**Lire d'abord [AUDIT.md](AUDIT.md).** Les notebooks n'ont pas été ré-exécutés : les jeux de données (parquet) ne sont pas dans le dépôt. L'audit s'appuie sur la lecture du code et des sorties enregistrées. Points majeurs :

- Les R² très élevés (0,996–0,997) reposent sur le SWI de la veille ; sans lui, le même transfert donne R² ≈ 0,52–0,54.
- Les découpages apprentissage/test sont aléatoires sur des points voisins dans l'espace et le temps.
- Les résultats ne sont pas reproductibles tant que les données et leurs sources ne sont pas documentées.

## Installation

```sh
conda env create -f environment.yml
conda activate climaterisk
jupyter lab
```

Les notebooks attendent des fichiers parquet locaux (`df_naq.parquet`, `df13.parquet`, `swi_clean.parquet`, …) construits à partir du SWI Safran, des argiles BRGM et d'Admin Express IGN ; leur reconstruction n'est pas encore scriptée.

## Historique de cette copie

- Notebook `SAR:CAR:KRIGING_NAQ.ipynb` renommé `SAR_CAR_KRIGING_NAQ.ipynb` : le caractère `:` rend le dépôt impossible à cloner sous Windows. Contenu inchangé.
- Aucun calcul ni résultat des notebooks n'a été modifié.
