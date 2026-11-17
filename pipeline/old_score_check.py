"""Vérifie l'ancien « score CatNat-like » (Bouches-du-Rhône, 119 communes) contre les arrêtés réels.

Entrées : data/drive/ (fichiers du Drive de l'équipe, voir data/drive_manifest.json).
Question : le score composite (aléa argile BRGM × part de jours secs) classe-t-il les communes comme la
fréquence réelle de reconnaissance 1989-2022 ? Comparaison avec la probabilité moyenne du modèle de fréquence.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from catnat.data import load_events
ROOT=Path(__file__).resolve().parents[1]

def bootstrap_spearman(a,b,n=2000,seed=0):
    rng=np.random.default_rng(seed);a=np.asarray(a);b=np.asarray(b);r=[]
    for _ in range(n):
        i=rng.integers(0,len(a),len(a));r.append(spearmanr(a[i],b[i])[0])
    return float(np.nanquantile(r,.05)),float(np.nanquantile(r,.95))

def main():
    ev=load_events();ev['year']=ev.start.dt.year
    sel=ev[(ev.insee.str.startswith('13'))&ev.year.between(1989,2022)]
    obs=sel.groupby(['insee','year']).size().reset_index().groupby('insee').size().rename('years_recognised')
    score=pd.read_parquet(ROOT/'data/drive/d13_model_score_catnatlike.parquet').rename(columns={'code_insee':'insee'})
    crit=pd.read_parquet(ROOT/'data/drive/d13_model_proxy_zone_critique.parquet').rename(columns={'code_insee':'insee'})[['insee','zone_critique']]
    d=score.merge(crit,on='insee',how='left').merge(obs,on='insee',how='left');d['years_recognised']=d.years_recognised.fillna(0)
    d['freq_observed']=d.years_recognised/34.
    pred=pd.read_parquet(ROOT/'data/processed/predictions.parquet')
    mp=pred[pred.insee.str.startswith('13')].groupby('insee').agg(p_model=('p_glm_complet','mean'),obs_rate=('y','mean')).reset_index();d=d.merge(mp,on='insee',how='left')
    out={'communes':int(len(d)),'years':[1989,2022],'mean_years_recognised':float(d.years_recognised.mean())}
    for name,col in [('score_catnat',d.score_catnat),('arg_norm',d.arg_norm),('dry_norm',d.dry_norm),('modele_frequence',d.p_model)]:
        ok=col.notna();rho=float(spearmanr(col[ok],d.freq_observed[ok])[0]);out[name]={'spearman':rho,'ci90':bootstrap_spearman(col[ok],d.freq_observed[ok])}
    z=d.groupby('zone_critique').freq_observed.agg(['mean','count']).reset_index();out['zone_critique']=z.to_dict('records')
    out['note']=("Le modèle de fréquence est évalué hors échantillon sur 1995-2022 ; le score d'origine n'est pas un modèle estimé. Les deux sont comparés sur la même fréquence observée 1989-2022 des communes du 13.")
    (ROOT/'reports/old_score_check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=1))

if __name__=='__main__':main()
