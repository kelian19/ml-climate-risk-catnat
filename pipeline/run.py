"""Construit la table, rejoue la validation année par année et écrit les résultats mesurés.

python -m pipeline.download   # une fois (≈ 155 Mo)
python -m pipeline.run
"""
import json,platform
from pathlib import Path
import importlib.metadata as md
import numpy as np
import pandas as pd
from catnat.table import build_table
from catnat.labels import publication_lag_table
from catnat.model import rolling_origin,FEATURE_SETS,glm_coefficients
from catnat.metrics import scores,by_year,calibration_table
ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'reports';FIG=REPORTS/'figures'
FIRST_TEST_YEAR=1995;LABEL_LAG=2;RECENT=(2010,2022)
MODELS=['p_constante','p_credibilite']+[f'p_{k}' for k in FEATURE_SETS]

def main():
    REPORTS.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True);(ROOT/'data/processed').mkdir(parents=True,exist_ok=True)
    table,events,meta=build_table()
    table.to_parquet(ROOT/'data/processed/commune_year.parquet',index=False)
    test_years=list(range(FIRST_TEST_YEAR,meta['last_mature_year']+1))
    pred,fitted=rolling_origin(table,test_years,label_lag=LABEL_LAG)
    pooled={m:scores(pred.y,pred[m],reference=pred.p_constante) for m in MODELS}
    recent=pred[pred.year.between(*RECENT)]
    pooled_recent={m:scores(recent.y,recent[m],reference=recent.p_constante) for m in MODELS}
    yearly={m:by_year(pred,m).to_dict('records') for m in MODELS}
    per_year_scores=[]
    for t,g in pred.groupby('year'):
        for m in MODELS:per_year_scores.append({'year':int(t),'model':m,**scores(g.y,g[m],reference=g.p_constante)})
    last=meta['last_mature_year']
    coefs=glm_coefficients(fitted[('glm_complet',last)],FEATURE_SETS['glm_complet'])
    calib={m:calibration_table(pred.y,pred[m]).to_dict('records') for m in ['p_credibilite','p_glm_complet','p_gbm_complet']}
    lags=publication_lag_table(events).round(3).reset_index().rename(columns={'start':'year'})
    versions={p:md.version(p) for p in ['numpy','pandas','scikit-learn','scipy','geopandas','pyproj','pyarrow']}
    result={'meta':meta,'protocol':{'test_years':test_years,'label_lag_years':LABEL_LAG,'split':'origine glissante par année ; apprentissage sur années ≤ t−2',
            'features':FEATURE_SETS,'climatology':'expansive, années antérieures seulement','credibility_k':3},
            'pooled':pooled,'pooled_recent':{'years':list(RECENT),'scores':pooled_recent},'per_year':per_year_scores,'by_year':yearly,'calibration':calib,
            'glm_complet_coefficients_last_year':coefs.to_dict('records'),'publication_lag':lags.to_dict('records'),
            'python':platform.python_version(),'versions':versions}
    (REPORTS/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
    pred.to_parquet(ROOT/'data/processed/predictions.parquet',index=False)
    figures(pred,calib,lags)
    from catnat.maps import make_maps
    result['maps']=make_maps(pred,ROOT/'data/raw',FIG)
    (REPORTS/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
    print(json.dumps({'meta':meta,'pooled':pooled},ensure_ascii=False,indent=1,default=float))

def figures(pred,calib,lags):
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    labels={'p_constante':'Constante','p_credibilite':'Crédibilité commune','p_glm_meteo':'GLM météo','p_glm_meteo_expo':'GLM météo + exposition','p_glm_complet':'GLM complet','p_gbm_complet':'GBM complet'}
    fig,ax=plt.subplots(figsize=(8,4))
    obs=pred.groupby('year').y.sum();ax.bar(obs.index,obs.values,color='#c9d6c2',label='Observé')
    for m,s in [('p_credibilite','--'),('p_glm_complet','-'),('p_gbm_complet',':')]:
        e=pred.groupby('year')[m].sum();ax.plot(e.index,e.values,s,marker='o',ms=3,label=labels[m])
    ax.set_ylabel('Communes reconnues');ax.set_title('Observé contre attendu par année (hors échantillon)');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(FIG/'observe_attendu.png',dpi=130);plt.close(fig)
    fig,ax=plt.subplots(figsize=(4.6,4.4))
    for m,c in calib.items():
        d=pd.DataFrame(c);ax.plot(d.p_mean,d.y_rate,marker='o',label=labels[m])
    ax.plot([0,1],[0,1],'k--',lw=.8);ax.set_xscale('symlog',linthresh=0.01);ax.set_yscale('symlog',linthresh=0.01)
    ax.set_xlabel('Probabilité prédite (décile)');ax.set_ylabel('Fréquence observée');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(FIG/'calibration.png',dpi=130);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.4))
    ax.plot(lags.year,lags['50%'],label='médiane');ax.plot(lags.year,lags['99%'],label='99 %');ax.set_ylabel('Années');ax.set_title('Retard fin d’événement → publication de l’arrêté');ax.legend();fig.tight_layout();fig.savefig(FIG/'retard_publication.png',dpi=130);plt.close(fig)

if __name__=='__main__':main()
