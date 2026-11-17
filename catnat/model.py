"""Modèles de fréquence annuelle de reconnaissance et validation « en temps réel ».

Pour prédire l'année t, on n'apprend que sur les années ≤ t − label_lag : les arrêtés d'une année
ne sont connus qu'après un ou deux ans (voir labels.publication_lag_table). Aucun découpage aléatoire.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier,RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .features import FEATURES_UNIFORM as FEATURES_METEO

FEATURES_EXPOSITION=['rga_mid_share','rga_high_share','rga_missing','log_population']
FEATURE_SETS={'glm_meteo':FEATURES_METEO,'glm_meteo_expo':FEATURES_METEO+FEATURES_EXPOSITION,
              'glm_complet':FEATURES_METEO+FEATURES_EXPOSITION+['hist_count'],
              'gbm_complet':FEATURES_METEO+FEATURES_EXPOSITION+['hist_count']}
FEATURES_ARGILE=['rga_c_low','rga_c_mid','rga_c_high','rga_c_missing']
FEATURE_SETS['glm_argile']=FEATURE_SETS['glm_complet']+FEATURES_ARGILE
FEATURE_SETS['gbm_argile']=FEATURE_SETS['gbm_complet']+FEATURES_ARGILE
FEATURE_SETS['rf_argile']=FEATURE_SETS['gbm_argile']
FEATURES_OFFICIEL=['off_rank_log','off_c1','off_c2']
FEATURE_SETS['glm_officiel']=FEATURE_SETS['glm_argile']+FEATURES_OFFICIEL
FEATURE_SETS['gbm_officiel']=FEATURE_SETS['gbm_argile']+FEATURES_OFFICIEL
CREDIBILITY_K=3.

def make_estimator(kind):
    if kind.startswith('glm'):return make_pipeline(StandardScaler(),LogisticRegression(C=1.,max_iter=1000))
    if kind.startswith('gbm'):return HistGradientBoostingClassifier(max_depth=4,learning_rate=0.05,max_iter=300,min_samples_leaf=200,l2_regularization=1.,random_state=0)
    if kind.startswith('rf'):return RandomForestClassifier(n_estimators=120,max_depth=10,min_samples_leaf=200,max_features='sqrt',n_jobs=-1,random_state=0)
    raise ValueError(kind)

def credibility_frequency(train,test,k=CREDIBILITY_K):
    """Référence actuarielle sans météo : fréquence propre à la commune, crédibilisée vers la fréquence globale,
    p = (Σy + k·p̄)/(n + k), estimée sur les seules années d'apprentissage."""
    pbar=train.y.mean();g=train.groupby('insee').y.agg(['sum','count'])
    p=(g['sum']+k*pbar)/(g['count']+k)
    return test.insee.map(p).fillna(pbar).to_numpy()

def rolling_origin(table,test_years,kinds=tuple(FEATURE_SETS),label_lag=2,min_train_years=3):
    """Prévisions hors échantillon année par année ; renvoie une ligne par commune-année testée."""
    out=[];fitted={}
    for t in test_years:
        train=table[table.year<=t-label_lag];test=table[table.year==t]
        if train.year.nunique()<min_train_years:raise ValueError(f'{t} : moins de {min_train_years} années d’apprentissage.')
        pred=test[['insee','year','y','n_arretes','population']].copy()
        pred['p_constante']=train.y.mean()
        pred['p_credibilite']=credibility_frequency(train,test)
        for kind in kinds:
            cols=FEATURE_SETS[kind];est=make_estimator(kind).fit(train[cols],train.y)
            pred[f'p_{kind}']=est.predict_proba(test[cols])[:,1];fitted[(kind,t)]=est
        pred['train_years']=f'{int(train.year.min())}–{int(train.year.max())}'
        out.append(pred)
    return pd.concat(out,ignore_index=True),fitted

def glm_coefficients(estimator,columns):
    """Coefficients sur variables standardisées et rapports de cotes pour un écart-type."""
    lr=estimator[-1];coef=lr.coef_[0]
    return pd.DataFrame({'variable':columns,'coef_std':coef,'odds_ratio_1sd':np.exp(coef)}).assign(intercept=lr.intercept_[0])

def spatial_block_validation(table,blocks,test_years,kind='glm_argile',label_lag=2):
    """Validation par blocs spatiaux : pour chaque année testée t et chaque bloc, apprentissage sur les années ≤ t − label_lag
    des communes des AUTRES blocs, prévision des communes du bloc retiré. Mesure la capacité à généraliser à une zone
    jamais vue (les prévisions « en temps réel » de rolling_origin voient toutes les zones à l'apprentissage)."""
    blocks=pd.Series(blocks);out=[];cols=FEATURE_SETS[kind]
    for t in test_years:
        for b in sorted(blocks.unique()):
            ins=blocks[blocks==b].index;train=table[(table.year<=t-label_lag)&~table.insee.isin(ins)];test=table[(table.year==t)&table.insee.isin(ins)]
            est=make_estimator(kind).fit(train[cols],train.y);pred=test[['insee','year','y']].copy();pred['p']=est.predict_proba(test[cols])[:,1];pred['block']=b
            pred['p_constante']=train.y.mean();out.append(pred)
    return pd.concat(out,ignore_index=True)
