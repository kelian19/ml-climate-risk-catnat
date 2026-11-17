"""Étude du SWI uniforme : prévision d'été, géostatistique, critère de période de retour, climat.

python -m pipeline.swi_study        # écrit reports/swi_study.json et reports/figures/swi_*.png
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from catnat.swi import load_cube,rolling_quarter_means
from catnat.forecast import predictor_table,rolling_forecast,forecast_scores,FEATURES
from catnat.geostat import knn_weights,morans_i,empirical_variogram,fit_variogram,MODELS,ordinary_kriging,block_cv_kriging
from catnat.criterion import criterion_cube,annual_flags,validate_against_decrees,return_period
from catnat.data import load_communes,assign_cells,load_events
from catnat.labels import build_labels,last_mature_year
ROOT=Path(__file__).resolve().parents[1];FIG=ROOT/'reports/figures'
FIRST_TEST=1985;T=25

def summer_forecast(cube,years,grid):
    tab=predictor_table(cube,years,grid.cell.values,grid.lat.values,grid.lon.values)
    last=int(tab.year.max());test_years=list(range(FIRST_TEST,last+1))
    pred=rolling_forecast(tab,test_years,kinds=('ridge','gbm','rf'))
    cols=['p_persistance','p_climatologie','p_ridge','p_gbm','p_rf']
    sc=forecast_scores(pred,cols)
    # Sous-période récente pour comparer aux années sèches.
    rec=pred[pred.year>=2000];sc_rec=forecast_scores(rec,cols)
    # Années sèches : pire quartile national.
    ann=pred.groupby('year').target.mean();dry=ann[ann<=ann.quantile(.25)].index
    sc_dry=forecast_scores(pred[pred.year.isin(dry)],cols)
    return tab,pred,sc,sc_rec,sc_dry,last

def geostat(cube,years,grid,year=2022):
    """SWI d'été (JJA) de l'année `year` : Moran, variogramme, krigeage, validation par blocs."""
    t=int(np.where(years==year)[0][0]);z=cube[t,:,5:8].mean(axis=1);ok=np.isfinite(z);xy=grid[['x93','y93']].to_numpy(float)[ok];z=z[ok]
    idx,w=knn_weights(xy,8);I,EI,p=morans_i(z,idx,w,permutations=199)
    lag,gam,cnt=empirical_variogram(xy,z,max_dist=400000.,bins=25)
    fits={m:fit_variogram(lag,gam,cnt,m) for m in MODELS};best=min(fits,key=lambda m:fits[m]['wrmse'])
    cv=block_cv_kriging(xy,z,fits[best],block_km=100.,n_neighbors=24,max_blocks=10)
    cv_small=block_cv_kriging(xy,z,fits[best],block_km=25.,n_neighbors=24,max_blocks=10)
    # Écart-type de référence : prédire par la moyenne globale.
    return {'year':year,'n_cells':int(len(z)),'moran_I':I,'moran_expected':EI,'moran_p':p,'variogram':{'lag_km':(lag/1000).tolist(),'gamma':gam.tolist(),'pairs':cnt.tolist()},
            'fits':fits,'best_model':best,'block_cv_100km':cv,'block_cv_25km':cv_small,'sd_field':float(z.std())}

def main():
    FIG.mkdir(parents=True,exist_ok=True)
    years,ids,cube,grid=load_cube()
    full=np.isfinite(cube[:,:,5:8]).all(axis=(1,2))
    last_full=int(years[full].max())
    out={'cube_shape':list(cube.shape),'years':[int(years[0]),int(years[-1])],'last_complete_summer':last_full}
    tab,pred,sc,sc_rec,sc_dry,last=summer_forecast(cube[:np.where(years==last_full)[0][0]+1],years[years<=last_full],grid)
    out['forecast']={'test_years':[FIRST_TEST,last],'scores':sc.round(4).to_dict('records'),'scores_2000_plus':sc_rec.round(4).to_dict('records'),'scores_dry_years':sc_dry.round(4).to_dict('records'),'features':FEATURES}
    out['geostat']=geostat(cube,years,grid)
    # Critère de période de retour reconstitué et validé contre les arrêtés.
    q=rolling_quarter_means(cube);events=load_events();mature=last_mature_year(events)
    com=assign_cells(load_communes(),grid[['cell','lon','lat']])
    lab=build_labels(events,com,list(range(1989,mature+1)))
    crit={}
    for Tn in (10,25,50):
        met,valid=criterion_cube(q,T=Tn);flag,ok=annual_flags(met,valid,years)
        yrs=list(range(1989,mature+1));fi=pd.DataFrame(flag[[y-years[0] for y in yrs]].T,index=ids,columns=yrs).stack().rename('flag').reset_index()
        fi.columns=['cell','year','flag'];fc=com[['code','cell']].rename(columns={'code':'insee'}).merge(fi,on='cell')[['insee','year','flag']];fc['flag']=fc.flag.astype(int)
        tab_c,d=validate_against_decrees(fc,lab);crit[str(Tn)]=tab_c
        by=d.groupby('year').agg(criterion=('flag','sum'),decrees=('y','sum'));crit[str(Tn)]['by_year']=by.reset_index().to_dict('records')
    out['criterion']=crit
    (ROOT/'reports/swi_study.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
    pred.to_parquet(ROOT/'data/processed/swi_forecast.parquet',index=False)
    print(json.dumps({k:out[k] for k in ['last_complete_summer','forecast']},ensure_ascii=False,indent=1,default=float)[:3500])

if __name__=='__main__':main()
