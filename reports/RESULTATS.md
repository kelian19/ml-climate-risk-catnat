# Résultats mesurés — fréquence de reconnaissance CatNat sécheresse

Table : 34746 communes × années 2006–2022 (590682 lignes), fréquence moyenne 4,29 %. Coupure des arrêtés : 2025-07-09 ; dernière année mûre : 2022.
Validation : origine glissante par année ; apprentissage sur années ≤ t−2 ; années de test 2010–2022.

## Scores agrégés hors échantillon

| Modèle | Log-loss | Gain vs constante | Brier | Gain Brier | AUC | Attendu | Observé |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fréquence constante | 0,2264 | 0,0 % | 0,0514 | 0,0 % | 0,638 | 7 738 | 24106 |
| Fréquence commune crédibilisée | 0,2319 | -2,5 % | 0,0493 | 4,1 % | 0,663 | 7 738 | 24106 |
| GLM météo | 0,2028 | 10,4 % | 0,0496 | 3,6 % | 0,804 | 13 153 | 24106 |
| GLM météo + exposition | 0,1900 | 16,1 % | 0,0460 | 10,5 % | 0,850 | 11 365 | 24106 |
| GLM complet | 0,1838 | 18,8 % | 0,0446 | 13,3 % | 0,861 | 11 646 | 24106 |
| GBM complet | 0,1929 | 14,8 % | 0,0435 | 15,4 % | 0,861 | 9 801 | 24106 |

## Observé contre attendu par année

| Année | Observé | Crédibilité | GLM complet | GBM complet | Obs./att. GLM | AUC GLM |
|---|---:|---:|---:|---:|---:|---:|
| 2010 | 100 | 216 | 235 | 265 | 0,42 | 0,908 |
| 2011 | 2247 | 311 | 622 | 525 | 3,61 | 0,906 |
| 2012 | 648 | 269 | 446 | 322 | 1,45 | 0,953 |
| 2013 | 23 | 598 | 22 | 38 | 1,06 | 0,956 |
| 2014 | 44 | 605 | 101 | 52 | 0,44 | 0,949 |
| 2015 | 205 | 533 | 624 | 378 | 0,33 | 0,954 |
| 2016 | 982 | 478 | 220 | 203 | 4,46 | 0,897 |
| 2017 | 2104 | 451 | 871 | 713 | 2,41 | 0,892 |
| 2018 | 4061 | 499 | 274 | 203 | 14,84 | 0,689 |
| 2019 | 2923 | 633 | 483 | 558 | 6,06 | 0,803 |
| 2020 | 3520 | 897 | 858 | 547 | 4,10 | 0,769 |
| 2021 | 355 | 1 041 | 378 | 401 | 0,94 | 0,853 |
| 2022 | 6894 | 1 207 | 6 513 | 5 596 | 1,06 | 0,784 |

## Coefficients du GLM complet (dernier apprentissage)

Variables standardisées ; rapport de cotes pour un écart-type. Les indicateurs météo sont corrélés : lecture conjointe.

| Variable | Coefficient | Rapport de cotes |
|---|---:|---:|
| `swi_jja_z` | 0,344 | 1,411 |
| `swi_son_z` | -0,339 | 0,712 |
| `swi_min_z` | -0,049 | 0,952 |
| `sswi3_sep` | -1,322 | 0,267 |
| `sswi12_dec` | -0,275 | 0,760 |
| `swi_jja_z_prev` | -0,229 | 0,796 |
| `rga_mid_share` | 0,410 | 1,507 |
| `rga_high_share` | 0,402 | 1,495 |
| `rga_missing` | -0,064 | 0,938 |
| `log_population` | 0,443 | 1,558 |
| `hist_count` | 0,361 | 1,435 |

## Retard de publication des arrêtés (années, fin d’événement → publication)

| Année d’événement | Arrêtés | Médiane | 90 % | 99 % | Max |
|---|---:|---:|---:|---:|---:|
| 2000 | 118 | 2,08 | 4,03 | 7,28 | 7,28 |
| 2001 | 24 | 2,07 | 5,04 | 5,95 | 5,95 |
| 2002 | 877 | 1,18 | 2,28 | 6,11 | 6,52 |
| 2003 | 4468 | 1,66 | 2,50 | 4,85 | 5,55 |
| 2004 | 287 | 4,20 | 4,95 | 6,95 | 7,38 |
| 2005 | 3233 | 2,55 | 3,18 | 3,80 | 6,38 |
| 2006 | 473 | 2,20 | 2,59 | 3,72 | 4,20 |
| 2007 | 459 | 1,35 | 1,55 | 2,95 | 3,20 |
| 2008 | 163 | 1,05 | 1,50 | 2,20 | 3,42 |
| 2009 | 615 | 1,20 | 1,39 | 2,22 | 8,90 |
| 2010 | 104 | 0,81 | 1,33 | 1,51 | 1,70 |
| 2011 | 2310 | 1,03 | 1,42 | 1,80 | 2,41 |
| 2012 | 658 | 0,64 | 1,46 | 1,84 | 3,15 |
| 2013 | 26 | 1,21 | 1,51 | 1,71 | 1,75 |
| 2014 | 44 | 1,06 | 1,66 | 1,66 | 1,66 |
| 2015 | 205 | 1,07 | 1,32 | 1,74 | 2,14 |
| 2016 | 993 | 1,06 | 1,49 | 1,74 | 5,05 |
| 2017 | 2119 | 0,74 | 1,22 | 1,47 | 3,73 |
| 2018 | 4093 | 0,46 | 0,88 | 1,54 | 3,06 |
| 2019 | 3335 | 0,71 | 1,22 | 1,65 | 2,97 |
| 2020 | 3734 | 0,63 | 0,88 | 1,72 | 2,47 |
| 2021 | 362 | 1,03 | 1,47 | 2,31 | 2,40 |
| 2022 | 7935 | 0,57 | 1,06 | 1,64 | 2,31 |
| 2023 | 1262 | 0,73 | 1,22 | 1,56 | 2,03 |

Figures : [observé/attendu](figures/observe_attendu.png), [calibration](figures/calibration.png), [retard de publication](figures/retard_publication.png).

Environnement : Python 3.12.13, numpy 2.5.5, pandas 3.1.1, scikit-learn 1.9.1, scipy 1.18.1, geopandas 1.2.0, pyproj 3.8.0, pyarrow 26.0.1.
