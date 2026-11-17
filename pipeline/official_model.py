"""Le critère officiel (rang sur 30 ans du SWI uniforme minimum, critères 1 et 2) améliore-t-il le modèle de fréquence ?

Mêmes protocole et années que le modèle de référence (origine glissante, 1995-2022). Écrit reports/official_model.json.

python -m pipeline.official_model
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from catnat.swi import load_cube
from catnat.official import official_features
from catnat.model import rolling_origin
from catnat.metrics import scores
ROOT=Path(__file__).resolve().parents[1]
KINDS=('glm_argile','glm_officiel','gbm_officiel')

def main():
    years,ids,cube,grid=load_cube();feats=official_features(cube,years,ids,12)
    table=pd.read_parquet(ROOT/'data/processed/commune_year.parquet').merge(feats,on=['cell','year'],how='left')
    miss=table[['off_rank_log','off_c1','off_c2']].isna().any(axis=1);print('lignes sans critère officiel :',int(miss.sum()),'années',sorted(table[miss].year.unique()))
    table=table[~miss].copy();mature=int(table.year.max())
    pred,_=rolling_origin(table,list(range(1995,mature+1)),kinds=KINDS);base=pred.p_constante;res={}
    for k in ('credibilite',)+KINDS:
        col=f'p_{k}';res[k]={'pooled':scores(pred.y,pred[col],base),'recent_2010_2022':scores(pred[pred.year>=2010].y,pred[pred.year>=2010][col],base[pred.year>=2010])}
        print(k,{a:round(b,4) for a,b in res[k]['pooled'].items() if a in ('log_loss_skill','auc')},'2010+',round(res[k]['recent_2010_2022']['log_loss_skill'],4),flush=True)
    (ROOT/'reports/official_model.json').write_text(json.dumps(res,ensure_ascii=False,indent=2,default=float),encoding='utf-8')

if __name__=='__main__':main()
