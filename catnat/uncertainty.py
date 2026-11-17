"""Intervalles d'incertitude du modèle de fréquence.

Deux intervalles distincts, à ne pas confondre :

1. **Incertitude d'estimation (probabilité d'une commune)** : bootstrap par blocs d'années. Les années sont
   les unités indépendantes (les communes d'une même année partagent le même climat), on rééchantillonne donc
   les années d'apprentissage avec remise, on réajuste le GLM et on prédit. Intervalle = quantiles des prédictions.
   Il ne contient pas le risque que le niveau annuel de reconnaissance change (procédure administrative).

2. **Intervalle de prédiction du nombre de communes reconnues** : le niveau annuel est le principal risque.
   On le calibre sur l'erreur de prévision réelle du backtest : quantiles du rapport observé/attendu
   (en log), appliqués à l'attendu de l'année cible. Sa couverture est contrôlée en validation croisée
   « une année laissée de côté » sur le backtest lui-même.
"""
import numpy as np
import pandas as pd

def bootstrap_probabilities(train,target,cols,make_estimator,n_boot=100,seed=0,commune_fraction=0.25):
    """Matrice (n_boot, n_cibles) de probabilités prédites. Chaque réplique : années d'apprentissage tirées
    avec remise, sous-échantillon fixe de communes pour borner le coût d'ajustement."""
    rng=np.random.default_rng(seed);years=np.sort(train.year.unique());codes=train.insee.unique()
    keep=set(rng.choice(codes,size=min(len(codes),max(int(len(codes)*commune_fraction),1000)),replace=False));sub=train[train.insee.isin(keep)]
    by_year={y:g for y,g in sub.groupby('year')}
    out=np.empty((n_boot,len(target)))
    for b in range(n_boot):
        drawn=rng.choice(years,size=len(years),replace=True)
        boot=pd.concat([by_year[y] for y in drawn],ignore_index=True)
        if boot.y.nunique()<2:raise ValueError('Réplique sans variation de la cible.')
        out[b]=make_estimator().fit(boot[cols],boot.y).predict_proba(target[cols])[:,1]
    return out

def quantile_bands(draws,level=0.90):
    a=(1-level)/2;return np.quantile(draws,a,axis=0),np.quantile(draws,1-a,axis=0)

def ratio_interval(ratios,expected,level=0.80):
    """Intervalle de prédiction du total : attendu × quantiles des rapports observé/attendu passés."""
    a=(1-level)/2;lo,hi=np.quantile(ratios,[a,1-a]);return expected*lo,expected*hi

def loo_year_coverage(by_year,level=0.80):
    """Couverture « une année laissée de côté » de l'intervalle de rapport, sur le backtest :
    pour chaque année, quantiles calculés sur toutes les autres années. Renvoie (couverture, table)."""
    ratio=(by_year.observed/by_year.expected).to_numpy();exp=by_year.expected.to_numpy();obs=by_year.observed.to_numpy();rows=[];hit=0
    for i in range(len(ratio)):
        lo,hi=ratio_interval(np.delete(ratio,i),exp[i],level);ok=lo<=obs[i]<=hi;hit+=ok
        rows.append({'year':int(by_year.year.iloc[i]),'observed':int(obs[i]),'expected':float(exp[i]),'low':float(lo),'high':float(hi),'covered':bool(ok)})
    return hit/len(ratio),pd.DataFrame(rows)
