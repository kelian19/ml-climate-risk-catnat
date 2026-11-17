# Audit du projet (lecture du code et des sorties enregistrées)

**Périmètre et méthode.** Les cinq notebooks ont été lus (code, texte, sorties enregistrées). **Aucun n'a été ré-exécuté** : les fichiers parquet qu'ils chargent ne sont pas dans le dépôt. Les chiffres cités sont ceux des sorties enregistrées ; ils ne sont ni confirmés ni infirmés par un nouveau calcul.

## 1. La cible est le SWI, pas la sinistralité
Tous les modèles prédisent `SWI` (indice d'humidité des sols). Aucun notebook ne mentionne de sinistre, d'arrêté CatNat ou de charge. Le titre « risque climatique CatNat » décrit l'application visée, pas ce qui est mesuré. Une conclusion sur le risque assuré demanderait de relier le SWI (ou une anomalie de SWI) à des sinistres de sécheresse observés.

## 2. Les R² dépendent du SWI de la veille
| Résultat enregistré | R² | RMSE |
|---|---:|---:|
| NAQ, RF avec `SWI_lag1` (`SAR_CAR_KRIGING_NAQ`) | 0,996 | 0,017 |
| Transfert RF NAQ → Grand Est avec `SWI_lag1` | 0,997 | 0,015 |
| RF NAQ sans `SWI_lag1` (`Transfer_NAQ_GE`, 200 000 points) | 0,521 | 0,196 |
| RF Grand Est sans `SWI_lag1` | 0,535 | 0,179 |

Le SWI est un indice lissé : prédire le SWI du jour par celui de la veille est presque une identité. Les scores avec `SWI_lag1` mesurent l'autorégression, pas l'apport des variables météo, argiles ou spatiales. Aucune **référence de persistance** (SWI(t) = SWI(t−1)) n'est publiée, alors qu'elle est la comparaison naturelle. Le notebook de transfert contient déjà l'analyse « sans lag » ; c'est elle qui devrait porter les conclusions.

## 3. Découpages aléatoires sur données dépendantes
`random_forest_13` et les notebooks de transfert séparent apprentissage et test par `train_test_split` aléatoire (`random_state=0`) sur des lignes point × jour (584 400 lignes pour le département 13). Des mailles voisines et des jours consécutifs, très corrélés, se retrouvent des deux côtés : les scores sont optimistes. Les alternatives usuelles sont un découpage par dates (années entières, avec embargo) et un découpage par blocs spatiaux. Résultat enregistré pour le 13 : RF R² 0,864 / RMSE 0,093, régression linéaire R² 0,733 / RMSE 0,131.

Le test NAQ → Grand Est est en revanche un vrai test hors région : c'est le protocole le plus solide du dépôt, une fois le lag retiré.

## 4. Variables explicatives
- `LAMBX` / `LAMBY` (coordonnées) sont des variables du modèle de transfert : un arbre peut mémoriser des zones, ce qui n'a pas de sens physique d'une région à l'autre.
- `SSWI_10J` est vraisemblablement dérivé du SWI (nom et usage ; la définition n'est pas documentée dans le dépôt) : à vérifier, car il pourrait fuir l'information de la cible.
- Les variables météo (`PRENEI`, `PRELIQ`, `T`, `FF`) sont contemporaines de la cible ; aucune prévision n'est donc évaluée.

## 5. Prédiction conforme (CQR)
Couverture empirique mesurée sur le Grand Est : 92,89 %, largeur moyenne 0,181. Le niveau nominal visé n'apparaît pas dans les sorties lues. La garantie de couverture de la CQR suppose l'échangeabilité entre calibration et test ; la calibration est faite sur NAQ et appliquée au Grand Est, ce qui viole cette hypothèse. La couverture observée est donc un constat, pas une garantie. Le centre de l'intervalle atteint R² 0,838 contre 0,997 pour le RF ponctuel : les deux chiffres n'ont pas la même signification.

## 6. Géostatistique
L'indice de Moran (0,638, p simulée 0,001) est calculé sur une seule date (1er janvier 2000, 1 325 points). Il établit une forte autocorrélation spatiale ce jour-là, pas dans la durée. SAR/CAR sont ajustés au niveau départemental (voisinage KNN, k = 4) sur une moyenne estivale : l'échelle diffère de celle des modèles de mailles, et les deux familles de modèles ne sont pas comparées sur la même base.

## 7. Reproductibilité
- Les jeux de données ne sont pas fournis ; le catalogue (`data_catalog.md`) contient des « … » à la place des URL, périodes, licences et dates de téléchargement. Les sources probables (SWI Safran, argiles BRGM, Admin Express IGN) ne sont pas versionnées.
- `environment.yml` ne déclare pas des paquets importés par les notebooks : `seaborn`, `esda`, `libpysal`, `spreg`, `gstools`, `statsmodels`.
- Chaque notebook pèse 0,6 à 1,9 Mo à cause des sorties embarquées ; plusieurs sorties contiennent des chemins de la machine d'origine.
- `par1.ipynb` ne contient que du code et sert d'exploration ; les cellules ont des chemins locaux.
- Un fichier nommé avec `:` empêchait le clonage sous Windows (corrigé dans cette copie).

## Suite recommandée
1. Fournir ou scripter l'acquisition des données (sources, versions, empreintes) et compléter le catalogue.
2. Remplacer les découpages aléatoires par des découpages par années et par blocs spatiaux ; ajouter la référence de persistance.
3. Fonder les conclusions sur les modèles sans `SWI_lag1` ; retirer ou justifier `LAMBX/LAMBY` et `SSWI_10J`.
4. Relier le SWI à des sinistres sécheresse observés avant toute conclusion assurantielle.
5. Extraire le code des notebooks en modules testés, avec intégration continue.
