# Résultats mesurés — fréquence de reconnaissance CatNat sécheresse

Table : 34746 communes × années 1989–2022 (1181364 lignes), fréquence moyenne 3,52 %. Coupure des arrêtés : 2025-07-09 ; dernière année mûre : 2022.
Validation : origine glissante par année ; apprentissage sur années ≤ t−2 ; années de test 1995–2022.

## Scores agrégés hors échantillon

| Modèle | Log-loss | Gain vs constante | Brier | Gain Brier | AUC | Attendu | Observé |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fréquence constante | 0,1542 | 0,0 % | 0,0339 | 0,0 % | 0,448 | 25 790 | 34001 |
| Fréquence commune crédibilisée | 0,1455 | 5,6 % | 0,0328 | 3,1 % | 0,702 | 25 790 | 34001 |
| GLM météo | 0,1353 | 12,2 % | 0,0325 | 4,0 % | 0,778 | 27 035 | 34001 |
| GLM météo + exposition | 0,1218 | 21,0 % | 0,0308 | 8,9 % | 0,854 | 26 408 | 34001 |
| GLM complet | 0,1210 | 21,5 % | 0,0311 | 8,1 % | 0,862 | 29 885 | 34001 |
| GBM complet | 0,1253 | 18,8 % | 0,0296 | 12,6 % | 0,841 | 24 783 | 34001 |
| GLM complet + aléa argile communal | 0,1151 | 25,4 % | 0,0303 | 10,6 % | 0,884 | 29 039 | 34001 |
| GBM + aléa argile communal | 0,1213 | 21,4 % | 0,0293 | 13,5 % | 0,864 | 24 564 | 34001 |

### Sous-période 2010–2022 (mêmes modèles, historique d’apprentissage plus long)

| Modèle | Log-loss | Gain vs constante | AUC | Attendu | Observé |
|---|---:|---:|---:|---:|---:|
| Fréquence constante | 0,2192 | 0,0 % | 0,552 | 11 149 | 24106 |
| Fréquence commune crédibilisée | 0,2110 | 3,7 % | 0,700 | 11 149 | 24106 |
| GLM météo | 0,1879 | 14,3 % | 0,796 | 12 973 | 24106 |
| GLM météo + exposition | 0,1730 | 21,1 % | 0,859 | 11 623 | 24106 |
| GLM complet | 0,1664 | 24,1 % | 0,867 | 12 866 | 24106 |
| GBM complet | 0,1770 | 19,3 % | 0,841 | 13 218 | 24106 |
| GLM complet + aléa argile communal | 0,1582 | 27,8 % | 0,892 | 12 305 | 24106 |
| GBM + aléa argile communal | 0,1686 | 23,1 % | 0,870 | 12 761 | 24106 |

## Cartes

![France](figures/carte_france_communes.png)

![Départements](figures/carte_departements.png)

Région détaillée : **Occitanie**, choisie car la plus touchée sur la période (fréquence observée 6,3 % des communes-années). Année détaillée : 2022, 1488 communes reconnues pour 904 attendues.

![Région](figures/carte_region_76.png)

Départements les plus sous-estimés (observé/attendu) :

| Département | Observé | Attendu | Ratio |
|---|---:|---:|---:|
| 58 | 560 | 105 | 5,31 |
| 71 | 1003 | 252 | 3,99 |
| 89 | 511 | 130 | 3,92 |
| 39 | 752 | 212 | 3,55 |
| 21 | 557 | 206 | 2,71 |
| 18 | 624 | 257 | 2,43 |
| 57 | 1206 | 504 | 2,39 |
| 52 | 226 | 97 | 2,34 |

## Observé contre attendu par année

| Année | Observé | Crédibilité | GLM complet | GBM complet | Obs./att. GLM | AUC GLM |
|---|---:|---:|---:|---:|---:|---:|
| 1995 | 333 | 1 484 | 2 564 | 1 035 | 0,13 | 0,846 |
| 1996 | 614 | 1 259 | 1 669 | 895 | 0,37 | 0,840 |
| 1997 | 351 | 1 127 | 2 050 | 720 | 0,17 | 0,886 |
| 1998 | 578 | 1 063 | 894 | 496 | 0,65 | 0,934 |
| 1999 | 87 | 984 | 597 | 359 | 0,15 | 0,938 |
| 2000 | 71 | 943 | 511 | 246 | 0,14 | 0,928 |
| 2001 | 15 | 865 | 846 | 479 | 0,02 | 0,786 |
| 2002 | 653 | 799 | 793 | 395 | 0,82 | 0,923 |
| 2003 | 4352 | 739 | 1 403 | 643 | 3,10 | 0,772 |
| 2004 | 77 | 733 | 498 | 652 | 0,15 | 0,902 |
| 2005 | 1521 | 974 | 1 716 | 2 589 | 0,89 | 0,902 |
| 2006 | 323 | 918 | 1 030 | 1 111 | 0,31 | 0,889 |
| 2007 | 203 | 953 | 644 | 665 | 0,32 | 0,954 |
| 2008 | 121 | 918 | 504 | 454 | 0,24 | 0,919 |
| 2009 | 596 | 881 | 1 299 | 827 | 0,46 | 0,869 |
| 2010 | 100 | 843 | 634 | 460 | 0,16 | 0,910 |
| 2011 | 2247 | 831 | 1 965 | 1 972 | 1,14 | 0,900 |
| 2012 | 648 | 798 | 557 | 604 | 1,16 | 0,955 |
| 2013 | 23 | 861 | 138 | 118 | 0,17 | 0,964 |
| 2014 | 44 | 852 | 451 | 248 | 0,10 | 0,964 |
| 2015 | 205 | 819 | 1 119 | 843 | 0,18 | 0,935 |
| 2016 | 982 | 789 | 304 | 229 | 3,23 | 0,916 |
| 2017 | 2104 | 767 | 1 165 | 708 | 1,81 | 0,886 |
| 2018 | 4061 | 775 | 616 | 281 | 6,59 | 0,791 |
| 2019 | 2923 | 821 | 852 | 876 | 3,43 | 0,788 |
| 2020 | 3520 | 929 | 894 | 1 232 | 3,94 | 0,804 |
| 2021 | 355 | 993 | 511 | 787 | 0,69 | 0,880 |
| 2022 | 6894 | 1 072 | 3 662 | 4 860 | 1,88 | 0,817 |

## Coefficients du GLM complet (dernier apprentissage)

Variables standardisées ; rapport de cotes pour un écart-type. Les indicateurs météo sont corrélés : lecture conjointe.

| Variable | Coefficient | Rapport de cotes |
|---|---:|---:|
| `swi_jja_z` | -0,386 | 0,680 |
| `swi_son_z` | -0,260 | 0,771 |
| `swi_min_z` | 0,135 | 1,145 |
| `swi_jja_z_prev` | 0,020 | 1,020 |
| `rp_max_log` | 0,870 | 2,386 |
| `rga_mid_share` | 0,292 | 1,338 |
| `rga_high_share` | 0,553 | 1,739 |
| `rga_missing` | -0,027 | 0,974 |
| `log_population` | 0,534 | 1,706 |
| `hist_count` | 0,248 | 1,282 |

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
