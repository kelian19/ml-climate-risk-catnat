"""Comparaison de modèles de fréquence (GLM, gradient boosting, forêt aléatoire, ensemble) et validation par blocs spatiaux.

1. validation « en temps réel » (origine glissante, apprentissage ≤ t − 2), mêmes variables, 1995–2022 ;
2. ensemble : moyenne des probabilités ;
3. validation par blocs spatiaux : on retire un bloc de communes (k-moyennes sur les coordonnées) de l'apprentissage et on le prévoit.

python -m pipeline.ml_compare
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from catnat.data import load_communes
from catnat.model import rolling_origin,spatial_block_validation
from catnat.metrics import scores,by_year
ROOT=Path(__file__).resolve().parents[1]
KINDS=('glm_argile','gbm_argile','rf_argile')
BLOCK_YEARS=[2003,2011,2015,2018,2019,2022]

def main():
    table=pd.read_parquet(ROOT/'data/processed/commune_year.parquet');mature=int(table.year.max())
    pred,_=rolling_origin(table,list(range(1995,mature+1)),kinds=KINDS);pred['p_ensemble']=pred[[f'p_{k}' for k in KINDS]].mean(axis=1)
    res={};base=pred.p_constante
    for col in ['p_credibilite']+[f'p_{k}' for k in KINDS]+['p_ensemble']:
        res[col[2:]]={'pooled':scores(pred.y,pred[col],base),'recent_2010_2022':scores(pred[pred.year>=2010].y,pred[pred.year>=2010][col],base[pred.year>=2010])}
        r=by_year(pred,col);res[col[2:]]['ratio_obs_exp_median']=float(r.ratio_obs_exp.median())
        res[col[2:]]['auc_by_year_min_max']=[float(x) for x in (pred.groupby('year').apply(lambda d:scores(d.y,d[col])['auc']).agg(['min','max']))]
        print(col,{k:round(v,4) for k,v in res[col[2:]]['pooled'].items() if k in ('log_loss_skill','auc')},flush=True)
    com=load_communes().set_index('code');codes=table.insee.unique();xy=com.loc[codes,['lon','lat']].to_numpy()
    blocks=pd.Series(KMeans(8,n_init=5,random_state=0).fit_predict(xy),index=codes)
    sp={}
    for kind in ('glm_argile','gbm_argile'):
        sb=spatial_block_validation(table,blocks,BLOCK_YEARS,kind);sp[kind]={'pooled':scores(sb.y,sb.p,sb.p_constante),'by_block_auc':{int(b):scores(d.y,d.p)['auc'] for b,d in sb.groupby('block')},
            'by_year':{int(y):scores(d.y,d.p,d.p_constante) for y,d in sb.groupby('year')}}
        tr=pred[pred.year.isin(BLOCK_YEARS)];sp[kind]['time_only_same_years']=scores(tr.y,tr[f'p_{kind}'],tr.p_constante)
        print(kind,'blocs spatiaux',{k:round(v,4) for k,v in sp[kind]['pooled'].items() if k in ('log_loss_skill','auc')},'| temps seul',{k:round(v,4) for k,v in sp[kind]['time_only_same_years'].items() if k in ('log_loss_skill','auc')},flush=True)
    out={'models':res,'spatial_blocks':sp,'n_blocks':8,'block_years':BLOCK_YEARS}
    (ROOT/'reports/ml_compare.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=float),encoding='utf-8');print('reports/ml_compare.json écrit')

if __name__=='__main__':main()
