# Sécheresse CatNat : SWI uniforme, fréquence de reconnaissance et intervalles d'incertitude

Projet actuariel sur le péril sécheresse (retrait-gonflement des argiles) du régime CatNat. Il s'appuie sur le **SWI uniforme** de Météo-France, l'indicateur du critère météorologique CatNat, et sur les arrêtés de reconnaissance par commune. Il répond à trois questions :

1. **Prévoir le SWI uniforme** d'été (prévision fin mai) et l'interpoler dans l'espace (variogramme, krigeage).
2. **Estimer la fréquence de reconnaissance** d'une commune pour une année donnée, avec un modèle validé hors échantillon.
3. **Donner un résultat avec intervalle** : probabilité par commune et nombre de communes reconnues, avec leurs intervalles.

Le projet d'origine (notebooks archivés dans [`archive/notebooks/`](archive/notebooks/), score composite sur le Drive de l'équipe) est audité dans [AUDIT.md](AUDIT.md).

## Résultat : sécheresse 2026 (arrêtés non encore publiés)

Données SWI uniforme de janvier à septembre 2026. Détail : [reports/ete_2026.json](reports/ete_2026.json), communes : [reports/ete_2026_communes.csv](reports/ete_2026_communes.csv) (probabilité et intervalle à 90 % par commune).

| | Valeur |
|---|---:|
| Sévérité (plus grande période de retour du SWI uniforme trimestriel) | la plus élevée des 35 années comparées |
| **Nombre attendu de communes reconnues** (modèle complet + aléa argile communal, SWI krigé) | **≈ 7 900** |
| Intervalle à 90 % de l'estimation (incertitude des paramètres, bootstrap par années) | 5 500 – 9 700 |
| Intervalle de prédiction à 80 % (erreur de niveau annuel du backtest) | 1 000 – 18 200 |
| Intervalle de prédiction à 90 % | 700 – 22 400 |
| Couverture réelle de ces intervalles, une année laissée de côté (28 années) | 79 % (nominal 80 %) ; 82 % (nominal 90 %) |

**Deux intervalles, deux sens.** Le premier mesure l'incertitude *statistique* du modèle ; il est étroit. Le second mesure ce qui compte vraiment : l'écart entre le nombre prédit et le nombre reconnu une année donnée, très large car le niveau annuel de reconnaissance n'est pas stationnaire. Sur les 28 années du backtest, le rapport observé/attendu a une médiane de 0,42 (déciles 0,12 et 2,4) ; de 2016 à 2022 il vaut 0,7 à 6,6 (médiane 3,1). **Le centre de l'intervalle de prédiction n'est donc pas fiable** : selon le régime retenu, la valeur centrale va d'environ 3 400 à bien plus de 7 900. L'ordre de grandeur annoncé est une enveloppe, pas une prévision ponctuelle. De plus, 2026 est plus sévère que toute année d'apprentissage : le modèle extrapole.

Régions les plus exposées (part attendue des communes) : Centre-Val de Loire 37 %, Île-de-France 36 %, Occitanie 34 %, Nouvelle-Aquitaine 31 %. Zoom communal sur le Centre-Val de Loire ci-dessous.

![Sécheresse 2026](reports/figures/pro_nowcast_2026.png)

![Éventail de prédiction](reports/figures/pro_eventail_prediction.png)

![Centre-Val de Loire](reports/figures/pro_region_24_2026.png)

## 1. SWI uniforme : prévision et géostatistique

Le SWI uniforme est celui du modèle SIM configuré avec un sol argileux et un couvert gazonné identiques sur tout le territoire (documentation Météo-France, `data/raw/swi_presentation.pdf`). Le fichier de suivi (1958–2026) et le fichier de référence CatNat (1960–2025) sont identiques sur leur recouvrement (vérifié).

**Prévision du SWI d'été (JJA) fin mai**, validation par origine glissante, test 1985–2026 :

| Modèle | RMSE | Corrélation | RMSE, années sèches |
|---|---:|---:|---:|
| Persistance (SWI d'été précédent) | 0,189 | 0,51 | 0,219 |
| Climatologie de la maille | 0,151 | 0,68 | 0,200 |
| **Ridge** | **0,123** | **0,77** | **0,114** |
| Forêt aléatoire | 0,135 | 0,72 | 0,132 |
| Gradient boosting | 0,147 | 0,68 | 0,144 |

Le modèle linéaire (ridge) bat les modèles non linéaires : il extrapole mieux la tendance climatique. Il prévoit un état hydrique, pas la météo de l'été, d'où la corrélation modeste au niveau national (0,50).

**Géostatistique** (SWI d'été 2022, 8 981 mailles) : indice de Moran I = 0,87 (p = 0,005 par permutations) ; variogramme sphérique de portée ≈ 237 km ; krigeage ordinaire validé par blocs spatiaux retirés : RMSE 0,039 (blocs de 100 km) pour un écart-type du champ de 0,085, couverture 97 % de l'intervalle à 95 %. Détail : [reports/swi_study.json](reports/swi_study.json).

![Krigeage du SWI uniforme](reports/figures/pro_krigeage_swi.png)

### Estimer le SWI uniforme là où la maille n'existe pas

Le SWI uniforme n'existe qu'aux 8 981 mailles. Une commune est estimée **au centre de la commune** par krigeage ordinaire en voisinage glissant (24 mailles, variogramme exponentiel standardisé ajusté sur les lags < 100 km, pépite ≈ 2 %). Les poids ne dépendent que de la géométrie : ils sont calculés une fois puis appliqués aux séries mensuelles 1959–2026 ([`catnat/geostat.py`](catnat/geostat.py), [`pipeline/spatial_interp.py`](pipeline/spatial_interp.py)). Validation en retirant 10 % des mailles au hasard (898 mailles × 68 étés) :

| Méthode | RMSE (SWI) | Couverture de l'intervalle à 95 % |
|---|---:|---:|
| Maille la plus proche | 0,0562 | — |
| Pondération inverse (IDW, 8 voisines) | 0,0373 | — |
| **Krigeage ordinaire** | **0,0359** | 95,6 % |

Le krigeage réduit l'erreur d'environ 36 % par rapport à la maille la plus proche, fait légèrement mieux que l'IDW et fournit un écart-type d'estimation calibré. Les corrections sont les plus fortes en relief (Alpes). Effet sur le modèle de fréquence : gain de log-loss 21,25 % → 21,53 %, AUC 0,861 → 0,862 (modeste : un centre de commune est en médiane à 3 km d'une maille).

![SWI krigé aux communes](reports/figures/pro_interpolation_communes.png)

**Climat observé** (pas de projections DRIAS/CMIP) : tendance du SWI d'été moyen national −0,021 par décennie (Theil–Sen, intervalle à 90 % [−0,034 ; −0,007], Mann–Kendall p = 0,004) ; 98 % des mailles à tendance négative, 61 % significativement. Test de sensibilité par décalage uniforme du SWI : [reports/climate.json](reports/climate.json).

![Étés secs](reports/figures/pro_swi_etes_secs.png)

**Critère météorologique reconstitué** (fenêtres glissantes de 3 mois, période de retour par maille sur les années antérieures) contre les arrêtés 1989–2022 :

| Période de retour | Sensibilité | Précision |
|---|---:|---:|
| 10 ans | 80 % | 5 % |
| 25 ans | 67 % | 7 % |
| 50 ans | 57 % | 9 % |

Le critère est nécessaire mais pas suffisant : la reconnaissance exige aussi un critère géotechnique (argile) et une demande. Les paramètres exacts de la circulaire ne sont pas publiés dans les données ; cette reconstitution est paramétrable et évaluée, pas officielle. Sa période de retour maximale entre comme variable (`rp_max_log`) dans le modèle de fréquence.

## 2. Modèle de fréquence de reconnaissance

Variable à expliquer : la commune a au moins un arrêté sécheresse pour un événement débutant l'année t (34 746 communes, 1989–2022). Validation « en temps réel » : apprentissage sur les années ≤ t − 2 (retard de publication des arrêtés), test sur l'année t entière, 1995–2022. Aucun découpage aléatoire.

| Modèle | Gain de log-loss vs constante, 1995–2022 | Idem 2010–2022 | AUC 1995–2022 |
|---|---:|---:|---:|
| Fréquence communale crédibilisée | 5,6 % | 3,7 % | 0,702 |
| GLM, SWI uniforme seul | 12,0 % | 13,9 % | 0,775 |
| GLM, SWI uniforme + exposition RGA | 20,7 % | 20,7 % | 0,852 |
| **GLM complet** (+ historique publié) | **21,3 %** | **23,7 %** | **0,861** |
| Gradient boosting | 18,0 % | 18,4 % | 0,837 |
| **GLM complet + aléa argile communal (BRGM)** | **25,4 %** | **27,8 %** | **0,884** (0,892 en 2010–2022) |

Les indicateurs sont calculés sans information future (climatologie expansive) ; l'historique de reconnaissance ne compte que les arrêtés publiés avant le 1er janvier de l'année prédite. Passer du SWI à sols réels au SWI uniforme ne change presque pas le pouvoir prédictif (21,2 % avant, 21,3 % après) mais aligne le modèle sur l'indicateur du dispositif.

![Observé contre attendu](reports/figures/observe_attendu.png)

La **classification** des communes est bonne (AUC de 0,69 à 0,96 selon l'année), le **niveau annuel** est le point faible (voir ci-dessus). Cartes France, départements et région : [reports/RESULTATS.md](reports/RESULTATS.md).

![Triptyque](reports/figures/pro_france_triptyque.png)

![Calendrier](reports/figures/pro_calendrier_departements.png)

## 3. Vérification de l'ancien score « CatNat-like » (Bouches-du-Rhône)

Les bases du Drive de l'équipe contiennent, pour les 119 communes du 13, un score composite (aléa argile BRGM normalisé × part de jours secs), et pour la Nouvelle-Aquitaine un score départemental. Contre la fréquence réelle de reconnaissance 1989–2022 des communes du 13 ([reports/old_score_check.json](reports/old_score_check.json)) :

| Indicateur | Corrélation de rang (Spearman) | Intervalle à 90 % (bootstrap) |
|---|---:|---:|
| Score composite d'origine | 0,28 | 0,13 – 0,42 |
| Aléa argile BRGM seul | **0,59** | 0,48 – 0,68 |
| Part de jours secs seule | −0,21 | −0,35 – −0,07 |
| Modèle de fréquence (probabilité moyenne) | 0,49 | 0,35 – 0,63 |

Le score composite est dégradé par sa composante « jours secs », anticorrélée avec la reconnaissance dans ce département (la sécheresse est quasi homogène dans le 13, ce sont les différences d'argile qui discriminent). L'aléa argile communal est le meilleur prédicteur du 13 : il surpasse notre exposition RGA, qui n'est disponible qu'à l'échelle de l'EPCI. 

**Intégré à toute la France** : la carte d'exposition BRGM 2025 (121 399 polygones, aléas faible, moyen, fort) est superposée aux contours communaux ([`pipeline/rga_communes.py`](pipeline/rga_communes.py)) pour obtenir la part de surface par classe. C'est l'amélioration la plus nette du modèle (gain 21,5 % → 25,4 %, AUC 0,862 → 0,884).

![Argile × sécheresse](reports/figures/pro_bivarie_argile_secheresse.png)

## Données et reproductibilité

Sources publiques : Météo-France (SWI uniforme suivi et référence CatNat, SIM mensuelle, points de grille), GASPAR (arrêtés), SDES (exposition RGA), geo.api.gouv.fr, Etalab (contours). `python -m pipeline.download` les télécharge (≈ 400 Mo, `data/raw/`, non versionné) avec empreintes SHA-256 dans [`data/manifest.json`](data/manifest.json). Les 22 fichiers du Drive de l'équipe sont dans `data/drive/` (non versionné) ; leur manifeste est [`data/drive_manifest.json`](data/drive_manifest.json). Catalogue : [data_catalog.md](data_catalog.md).

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt   # Windows : .venv\Scripts\
python -m pipeline.download      # sources publiques
python -m pipeline.run           # table, validation 1995–2022, cartes (≈ 30 min)
python -m pipeline.swi_study     # prévision du SWI, géostatistique, critère
python -m pipeline.spatial_interp   # krigeage du SWI aux centres de communes (data/processed/swi_commune.npz)
python -m pipeline.rga_communes  # aléa argile BRGM par commune (nécessite data/raw/rga_brgm/alea.zip, 623 Mo)
python -m pipeline.nowcast       # estimation de l'année en cours avec intervalles
python -m pipeline.climate_study # tendances et sensibilité
python -m pipeline.figures_pro   # figures détaillées (reports/figures/pro_*.png)
python -m pipeline.make_tables   # tableaux de la note LaTeX
python -m pipeline.old_score_check   # ancien score contre arrêtés (nécessite data/drive/)
python -m pytest tests -q        # tests unitaires (+ contrôles sur données réelles si présentes)
```

## Limites

- **Fréquence, pas charge** : aucune donnée publique de sinistres ou de coûts à la commune. Pas de prime pure.
- **Niveau annuel non stationnaire** : la procédure de reconnaissance et ses critères ont évolué ; c'est la première source d'incertitude (intervalle de prédiction très large).
- Exposition RGA par EPCI, population et contours : photographies récentes appliquées à toutes les années ; l'aléa argile communal est calculé sur des contours simplifiés à 100 m.
- Le critère météorologique est une reconstitution, pas le critère officiel.
- 2026 : données provisoires (jusqu'en septembre), sévérité hors de la plage d'apprentissage.
- **Climat** : tendances observées et sensibilité par décalage uniforme, pas de projections climatiques (DRIAS, CMIP).
- Modèles de fréquence limités au GLM et au gradient boosting ; la forêt aléatoire n'est utilisée que pour la prévision du SWI.

## Organisation

`catnat/` (données, SWI uniforme, critère, prévision, géostatistique, variables, modèles, incertitude, cartes), `pipeline/` (exécutions), `tests/` (tests unitaires et contrôles sur données réelles), `reports/` (résultats mesurés, figures), `docs/latex/` (note de 12 pages : [`note_catnat.pdf`](docs/latex/note_catnat.pdf), compilée avec Tectonic depuis `note_catnat.tex` et les tableaux générés `tables.tex`), `archive/notebooks/` (version d'origine).
