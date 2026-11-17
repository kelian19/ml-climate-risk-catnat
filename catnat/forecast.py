"""Prévision du SWI uniforme trimestriel d'été (juin-juillet-août) fin mai, validée année par année.

Cible : SWI_JJA = moyenne juin-juillet-août du SWI uniforme de la maille.
Prédicteurs, tous connus fin mai de l'année t :
  - SWI de mai (état hydrique de départ) et moyenne mars-mai ;
  - SWI moyen de l'hiver précédent (décembre-février) et de l'été précédent ;
  - climatologie JJA de la maille estimée sur les années antérieures seulement ;
  - tendance : année (progression du climat).
La météo de l'été à venir n'est pas connue : la prévision est donc une prévision d'état hydrique, pas météo.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor,RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES=['swi_may','swi_mam','swi_win_prev','swi_jja_prev','clim_jja','year_std']

def predictor_table(cube,years,cell_ids,lat=None,lon=None):
    """Une ligne par maille et année t (à partir de la 2e année) avec prédicteurs et cible SWI_JJA."""
    y,c,_=cube.shape;rows=[]
    clim_sum=np.nancumsum(cube[:,:,5:8].mean(axis=2),axis=0)
    for t in range(1,y):
        if not np.isfinite(cube[t,:,5:8]).all():continue
        win=np.concatenate([cube[t-1,:,11:12],cube[t,:,0:2]],axis=1).mean(axis=1)  # déc t−1, janv, févr
        n=max(t,1)
        d={'cell':cell_ids,'year':np.full(c,years[t]),'swi_may':cube[t,:,4],'swi_mam':cube[t,:,2:5].mean(axis=1),
           'swi_win_prev':win,'swi_jja_prev':cube[t-1,:,5:8].mean(axis=1),'clim_jja':clim_sum[t-1]/n,'target':cube[t,:,5:8].mean(axis=1)}
        rows.append(pd.DataFrame(d))
    out=pd.concat(rows,ignore_index=True)
    out['year_std']=(out.year-1990)/30.
    if lat is not None:out=out.merge(pd.DataFrame({'cell':cell_ids,'lat':lat,'lon':lon}),on='cell')
    return out

def make_model(kind):
    if kind=='ridge':return make_pipeline(StandardScaler(),Ridge(alpha=1.))
    if kind=='gbm':return HistGradientBoostingRegressor(max_depth=5,learning_rate=0.06,max_iter=300,min_samples_leaf=200,l2_regularization=1.,random_state=0)
    if kind=='rf':return RandomForestRegressor(n_estimators=60,min_samples_leaf=50,max_features=0.6,n_jobs=-1,random_state=0)
    raise ValueError(kind)

def rolling_forecast(table,test_years,kinds=('ridge','gbm','rf'),min_train_years=15,features=FEATURES,sample=60000,seed=0):
    """Origine glissante : apprentissage sur les années < t (le SWI d'été de l'année t−1 est entièrement connu en mai t),
    prédiction de l'année t entière. Sous-échantillonnage aléatoire des lignes d'apprentissage (taille fixe) pour borner le coût."""
    rng=np.random.default_rng(seed);out=[]
    for t in test_years:
        train=table[table.year<t];test=table[table.year==t]
        if train.year.nunique()<min_train_years:raise ValueError(f'{t} : moins de {min_train_years} années d’apprentissage.')
        tr=train.iloc[rng.choice(len(train),size=min(sample,len(train)),replace=False)]
        pred=test[['cell','year','target']].copy()
        pred['p_persistance']=test.swi_jja_prev;pred['p_climatologie']=test.clim_jja
        for k in kinds:pred[f'p_{k}']=make_model(k).fit(tr[features],tr.target).predict(test[features])
        out.append(pred)
    return pd.concat(out,ignore_index=True)

def forecast_scores(pred,cols):
    """RMSE et corrélation par modèle, plus RMSE sur l'anomalie annuelle moyenne nationale."""
    rows=[]
    for c in cols:
        e=pred[c]-pred.target
        by=pred.groupby('year').agg(t=('target','mean'),p=(c,'mean'))
        rows.append({'model':c,'rmse':float(np.sqrt((e**2).mean())),'mae':float(e.abs().mean()),'corr':float(np.corrcoef(pred[c],pred.target)[0,1]),
                     'national_rmse':float(np.sqrt(((by.p-by.t)**2).mean())),'national_corr':float(np.corrcoef(by.p,by.t)[0,1])})
    return pd.DataFrame(rows)
