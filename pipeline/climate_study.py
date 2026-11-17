"""Tendances du SWI uniforme et sensibilité du modèle de fréquence à un climat plus sec.

python -m pipeline.climate_study     # reports/climate.json, reports/figures/climate_*.png
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from catnat.swi import load_cube
from catnat.climate import summer_means,cell_trends,severe_summer_frequency,decade_table,national_trend_per_decade
from catnat.features import build_features_uniform,FEATURES_UNIFORM
from catnat.model import FEATURE_SETS,make_estimator
ROOT=Path(__file__).resolve().parents[1];FIG=ROOT/'reports/figures'
KIND='glm_argile';BASE_YEARS=(2018,2022);SHIFTS=[0.05,0.0,-0.03,-0.06,-0.10]

def main():
    FIG.mkdir(parents=True,exist_ok=True)
    years,ids,cube,grid=load_cube();summer=summer_means(cube)
    complete=np.isfinite(summer).all(axis=1);ys=years[complete];sm=summer[complete]
    nat=national_trend_per_decade(sm,ys);slope,p=cell_trends(sm,ys.astype(float))
    freq=severe_summer_frequency(sm,ys);dec=decade_table(freq,ys)
    out={'years':[int(ys[0]),int(ys[-1])],'national_trend':nat,'cells':{'n':int(len(slope)),'share_negative':float(np.nanmean(slope<0)),
         'share_significant_negative_5pct':float(np.nanmean((slope<0)&(p<0.05))),'median_slope_per_decade':float(np.nanmedian(slope)*10)},
         'severe_summer_share_by_decade':dec,'sd_national_summer':float(np.nanstd(np.nanmean(sm,axis=1),ddof=1)),
         'caveat':'Tendances de la réanalyse SIM ; les mailles voisines sont corrélées, le nombre de mailles significatives ne se lit pas comme autant de tests indépendants.'}
    # Sensibilité du modèle de fréquence : déplacement du SWI de l'année de base (tous les mois), modèle appris sur t-2 années.
    table=pd.read_parquet(ROOT/'data/processed/commune_year.parquet');cols=FEATURE_SETS[KIND];rows=[]
    zc=np.load(ROOT/'data/processed/swi_commune.npz',allow_pickle=True);ycube=zc['cube'].astype(float);ycodes=zc['codes']
    for Y in BASE_YEARS:
        tr=table[table.year<=Y-2];est=make_estimator(KIND).fit(tr[cols],tr.y);base=table[table.year==Y].copy()
        ti=int(np.where(years==Y)[0][0])
        for sh in SHIFTS:
            c2=ycube[:ti+1].copy();c2[ti]=c2[ti]+sh
            f=build_features_uniform(c2,years[:ti+1],ycodes,10).rename(columns={'cell':'insee'})
            f=f[f.year==Y][['insee']+FEATURES_UNIFORM]
            d=base.drop(columns=FEATURES_UNIFORM).merge(f,on='insee',how='left')
            rows.append({'base_year':Y,'shift':sh,'shift_sd':sh/out['sd_national_summer'],'expected_communes':float(est.predict_proba(d[cols])[:,1].sum()),'observed_communes':int(base.y.sum())})
    sc=pd.DataFrame(rows);out['sensitivity']=sc.to_dict('records')
    (ROOT/'reports/climate.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8.5,3.8));nat_series=np.nanmean(sm,axis=1);ax.plot(ys,nat_series,'-o',ms=3,color='#174f43')
    tr_line=np.polyval(np.polyfit(ys,nat_series,1),ys);ax.plot(ys,tr_line,'--',color='#b24a3a',label=f"tendance ({nat['per_decade']:+.3f} par décennie)")
    ax.set_ylabel('SWI uniforme JJA, moyenne nationale');ax.legend();fig.tight_layout();fig.savefig(FIG/'climate_tendance.png',dpi=130);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.5,3.8))
    for Y in BASE_YEARS:s=sc[sc.base_year==Y];ax.plot(s['shift'],s.expected_communes,'-o',label=f'Année de base {Y} (observé {int(s.observed_communes.iloc[0])})')
    ax.set_xlabel('Déplacement du SWI de l’année (unités de SWI)');ax.set_ylabel('Communes reconnues attendues');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(FIG/'climate_sensibilite.png',dpi=130);plt.close(fig)
    print(json.dumps({k:out[k] for k in ['national_trend','cells','severe_summer_share_by_decade']},ensure_ascii=False,indent=1,default=float));print(sc.round(1).to_string(index=False))

if __name__=='__main__':main()
