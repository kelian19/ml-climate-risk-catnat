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

# --- Choix d'un intervalle unique, évalué en temps réel -------------------------------------------------------------
# Méthodes candidates pour l'intervalle de prédiction du rapport observé/attendu d'une année future, à partir des
# rapports des années passées : quantiles empiriques ou loi log-normale (avec facteur de prédiction √(1 + 1/n) et quantile
# de Student), sur tout l'historique ou sur les `RECENT` dernières années disponibles.
RECENT=10
METHODS=('empirique_tout','empirique_recent','lognormal_tout','lognormal_recent')

def ratio_bounds(past,method,level):
    """Bornes (basse, haute) du rapport observé/attendu à partir des rapports passés (ordre chronologique)."""
    from scipy.stats import t as student
    r=np.asarray(past,float);r=r[-RECENT:] if method.endswith('recent') else r
    a=(1-level)/2
    if method.startswith('empirique'):return tuple(np.quantile(r,[a,1-a]))
    lr=np.log(r);n=len(lr);m=lr.mean();s=lr.std(ddof=1)*np.sqrt(1+1/n);k=student.ppf(1-a,n-1)
    return float(np.exp(m-k*s)),float(np.exp(m+k*s))

def interval_score(lo,hi,y,level):
    """Score d'intervalle (Gneiting et Raftery 2007), en log : largeur + pénalité 2/α par unité de dépassement. Plus bas = mieux."""
    a=1-level;l,u,v=np.log(lo),np.log(hi),np.log(y)
    return (u-l)+(2/a)*max(l-v,0)+(2/a)*max(v-u,0)

def realtime_evaluation(by_year,level=0.90,label_lag=2,min_years=8,methods=METHODS):
    """Pour chaque année t, intervalle construit avec les seuls rapports des années ≤ t − label_lag (connus à cette date),
    appliqué à l'attendu de t. Renvoie (résumé par méthode, détail par année)."""
    d=by_year.sort_values('year');ratio=dict(zip(d.year,d.observed/d.expected));rows=[]
    for _,row in d.iterrows():
        t=int(row.year);past=[ratio[y] for y in sorted(ratio) if y<=t-label_lag]
        if len(past)<min_years:continue
        for m in methods:
            lo,hi=ratio_bounds(past,m,level);L,H=row.expected*lo,row.expected*hi
            rows.append({'year':t,'method':m,'low':L,'high':H,'observed':int(row.observed),'covered':bool(L<=row.observed<=H),
                         'log_width':float(np.log(hi/lo)),'interval_score':float(interval_score(L,H,max(row.observed,1),level))})
    det=pd.DataFrame(rows)
    summ=det.groupby('method').agg(years=('year','size'),hits=('covered','sum'),coverage=('covered','mean'),mean_log_width=('log_width','mean'),mean_interval_score=('interval_score','mean')).reset_index()
    from scipy.stats import binom
    # Test unilatéral de sous-couverture : P(X ≤ couvertures observées) si la couverture vraie était le niveau nominal.
    summ['coverage_pvalue']=[float(binom.cdf(h,n,level)) for h,n in zip(summ.hits,summ.years)];summ['calibrated']=summ.coverage_pvalue>=0.05
    return summ.sort_values(['calibrated','mean_interval_score'],ascending=[False,True]).reset_index(drop=True),det

def choose_interval(by_year,expected,level=0.90,label_lag=2):
    """Règle fixée avant de voir les résultats : (1) on écarte les méthodes dont la sous-couverture en temps réel est
    significative (test binomial unilatéral à 5 %) ; (2) parmi les autres, plus faible score d'intervalle moyen (règle de
    score propre : elle récompense à la fois la couverture et l'étroitesse). La méthode est ensuite appliquée à l'année
    cible avec tous les rapports disponibles."""
    summ,det=realtime_evaluation(by_year,level,label_lag);best=summ.iloc[0]
    d=by_year.sort_values('year');lo,hi=ratio_bounds((d.observed/d.expected).to_numpy(),best.method,level)
    # Si aucune méthode n'est compatible (rupture de régime), on garde la meilleure au score et on le signale : 'calibrated' = False.
    return {'level':level,'method':best.method,'low':float(expected*lo),'high':float(expected*hi),'ratio_bounds':[float(lo),float(hi)],
            'realtime_coverage':float(best.coverage),'realtime_years':int(best.years),'realtime_coverage_pvalue':float(best.coverage_pvalue),'calibrated':bool(best.calibrated),
            'rule':'couverture non significativement inférieure au niveau (binomial unilatéral 5 %), puis score d’intervalle minimal',
            'evaluation':summ.to_dict('records')},det
