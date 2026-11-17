# Catalogue des données

Toutes les sources sont publiques. `python -m pipeline.download` les télécharge dans `data/raw/` et enregistre URL, taille, date et SHA-256 dans [`data/manifest.json`](data/manifest.json) ; un fichier dont l'empreinte change est refusé sans `--update`.

| Fichier | Source | Contenu utilisé | Remarques |
|---|---|---|---|
| `MENS_SIM2_1958…2025.csv.gz` | Météo-France, « Données changement climatique - SIM mensuelle », data.gouv.fr | SWI, SSWI3, SSWI12 mensuels par maille Safran (8 km), coordonnées Lambert II étendu (hm) | 9 892 mailles par an ; les 8 981 du shapefile sont retenues. 1958 est partiel (août–décembre) : la série utilisée commence en 1959. |
| `SHP_SIM_FRANCE.*` | Même jeu | Point central de chaque maille (lat/lon) | Rattachement commune → maille par plus proche voisin en Lambert-93. |
| `catnat.csv` | data.gouv.fr, « Arrêtés de catastrophe naturelle par commune » (base GASPAR) | Code INSEE, péril, dates de début et fin d'événement, date de publication | Fichier sans en-tête, séparateur `;`. Périls retenus : « Sécheresse » et « Retrait-gonflement des argiles ». |
| `rga_epci.csv` | SDES, exposition au retrait-gonflement des argiles par EPCI | Surfaces en aléa moyen (RGA2) et fort (RGA3) | Valeurs secrètes laissées manquantes ; part calculée sur la surface de l'EPCI (somme de ses communes). |
| `communes.json` | geo.api.gouv.fr | Code, centre, population, surface, EPCI | Référentiel actuel ; communes d'outre-mer exclues. |
| `communes-100m.geojson.gz` | Etalab, contours administratifs 2026 (simplifiés à 100 m), data.gouv.fr | Polygones des communes, département, région | Cartes uniquement ; polygones invalides réparés après reprojection. |
| `data/nowcast/MENS_SIM2_2026.csv.gz` | Météo-France, SIM mensuelle de l'année en cours | Estimation 2026 | Fichier provisoire mis à jour chaque mois ; empreinte enregistrée dans `reports/ete_2026.json`. |
| `swi_mailles.csv`, `swi_presentation.pdf` | Météo-France, SWI uniforme (suivi 1958–2026, référence CatNat 1960–2025), data.gouv.fr | SWI uniforme mensuel par maille, indicateur du critère CatNat | Noms raccourcis localement (limite de 260 caractères sous Windows). |
| `rga_brgm/alea.zip` (623 Mo) | BRGM / Géorisques, carte d'exposition au retrait-gonflement des argiles 2025 | 121 399 polygones, aléas faible, moyen, fort | Superposé aux contours communaux : part de surface par classe (`data/raw/rga_commune.csv`). |
| `data/drive/` (22 fichiers) | Drive de l'équipe | Score « CatNat-like » d'origine, bases communales du 13, départementales de Nouvelle-Aquitaine | Usage : vérification de l'ancien score (`pipeline/old_score_check.py`). Manifeste : `data/drive_manifest.json`. |
| `data/processed/swi_commune.npz` | Produit par `pipeline/spatial_interp.py` | SWI uniforme mensuel krigé au centre de chaque commune, variance de krigeage | Non versionné, régénérable. |
| `officiel/rapport_mf_2024.pdf` | Météo-France, rapport météorologique « Analyse de la sécheresse géotechnique, année 2024 » (DCSC/ACS, 27 janvier 2025), 466 Ko | Définition officielle du critère météorologique (circulaire IOME2322937C) : minimum mensuel annuel, rang sur 30 ans, critères 1 et 2 | Appliqué dans `catnat/official.py` ; reproduit exactement les 17 / 34 / 47 mailles du rapport pour 2024 (test). |
