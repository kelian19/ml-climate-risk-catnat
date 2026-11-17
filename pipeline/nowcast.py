"""Estimation de l'épisode de sécheresse de l'année en cours (arrêtés non encore publiés).

Le modèle « complet » est réentraîné sur des indicateurs arrêtés au dernier mois disponible de l'année en
cours (pour toutes les années, afin que les variables aient le même sens), sur les années mûres uniquement.
L'incertitude annuelle est tirée du backtest du même modèle : distribution des rapports observé/attendu.

python -m pipeline.nowcast            # fichier SIM de l'année en cours dans data/nowcast/
"""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from catnat.data import RAW,load_cells,load_communes,assign_cells,load_sim,load_events,load_rga,load_rga_commune
from catnat.features import build_features_uniform,FEATURES_UNIFORM
from catnat.swi import load_cube
from catnat.official import official_features
from catnat.labels import last_mature_year,build_labels,history_counts
from catnat.model import FEATURE_SETS,make_estimator,rolling_origin
from catnat.uncertainty import bootstrap_probabilities,quantile_bands,ratio_interval,loo_year_coverage
from catnat.maps import load_contours,REGIONS
from catnat.table import FIRST_SIM_YEAR,FIRST_LABEL_YEAR,CLIMATOLOGY_MIN_YEARS
ROOT=Path(__file__).resolve().parents[1]
NOW=ROOT/'data/nowcast';FIG=ROOT/'reports/figures'
YEAR=2026;FIRST_TEST_YEAR=1995;KIND='glm_officiel'

def load_current(year=YEAR):
    path=NOW/f'MENS_SIM2_{year}.csv.gz'
    if not path.exists():
        import urllib.request;NOW.mkdir(parents=True,exist_ok=True)
        urllib.request.urlretrieve(f'https://meteofrance.s3.sbg.io.cloud.ovh.net/data/REF_CC/SIM_MENS/MENS_SIM2_{year}.csv.gz',path)
    s=pd.read_csv(path,sep=';',usecols=['LAMBX','LAMBY','DATE','SWI','SSWI3','SSWI12'])
    s['year']=s.DATE//100;s['month']=s.DATE%100
    return s.drop(columns='DATE'),hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    years_u,ids_u,cube,grid=load_cube();communes=assign_cells(load_communes(),grid[['cell','lon','lat']]);events=load_events();mature=last_mature_year(events)
    digest=hashlib.sha256((RAW/'swi_uniforme.2026.csv.gz').read_bytes()).hexdigest()
    last_month=int(np.isfinite(cube[-1,0]).sum())
    z=np.load(ROOT/'data/processed/swi_commune.npz',allow_pickle=True)   # SWI uniforme krigé au centre des communes
    feats=build_features_uniform(z['cube'].astype(float),z['years'],z['codes'],CLIMATOLOGY_MIN_YEARS,last_month=last_month).rename(columns={'cell':'insee'})
    years=[y for y in range(FIRST_LABEL_YEAR,mature+1)]+[YEAR]
    t=build_labels(events,communes,years)
    t=t.merge(communes[['code','codeDepartement','codeEpci','population','cell']],left_on='insee',right_on='code').drop(columns='code')
    t=t.merge(feats,on=['insee','year'],how='left').merge(history_counts(events,communes,years),on=['insee','year'],how='left')
    t['hist_count']=t.hist_count.fillna(0)
    t=t.merge(official_features(cube,years_u,ids_u,last_month),on=['cell','year'],how='left')   # critère officiel, mois ≤ last_month
    t=t.merge(load_rga(RAW,communes),on='codeEpci',how='left');t['rga_missing']=t.rga_mid_share.isna().astype(int)
    pc=load_rga_commune(RAW);t=t.merge(pc,on='insee',how='left');t['rga_c_missing']=t.rga_c_mid.isna().astype(int)
    for c_ in ('rga_c_low','rga_c_mid','rga_c_high'):t[c_]=t[c_].fillna(0.)
    t[['rga_mid_share','rga_high_share']]=t[['rga_mid_share','rga_high_share']].fillna(0);t['log_population']=np.log1p(t.population.fillna(0))
    hist=t[t.year<=mature];cur=t[t.year==YEAR].copy()
    cols=FEATURE_SETS[KIND]
    assert all(c in t.columns for c in cols)
    if cur[cols].isna().any().any():raise ValueError('Indicateurs manquants pour l’année en cours.')
    # Backtest du même modèle (mêmes indicateurs arrêtés au mois last_month).
    pred,_=rolling_origin(hist,range(FIRST_TEST_YEAR,mature+1),kinds=(KIND,))
    ratios=pred.groupby('year').apply(lambda g:g.y.sum()/g[f'p_{KIND}'].sum(),include_groups=False)
    est=make_estimator(KIND).fit(hist[cols],hist.y)
    cur['p']=est.predict_proba(cur[cols])[:,1];expected=float(cur.p.sum())
    q=np.quantile(ratios,[.1,.5,.9])
    # Intervalles : (1) incertitude d'estimation par bootstrap d'années ; (2) prédiction du total par rapports observé/attendu du backtest.
    draws=bootstrap_probabilities(hist,cur,cols,lambda:make_estimator(KIND),n_boot=100,seed=0)
    cur['p_lo'],cur['p_hi']=quantile_bands(draws,0.9);tot=draws.sum(axis=1)*(1/1.0)
    by=pred.groupby('year').agg(observed=('y','sum'),expected=(f'p_{KIND}','sum')).reset_index()
    cov80,_=loo_year_coverage(by,0.8);cov90,_=loo_year_coverage(by,0.9)
    pi80=ratio_interval((by.observed/by.expected).to_numpy(),expected,0.8);pi90=ratio_interval((by.observed/by.expected).to_numpy(),expected,0.9)
    cur[['insee','p','p_lo','p_hi']].to_csv(ROOT/'reports/ete_2026_communes.csv',index=False)
    # Sévérité nationale (moyenne sur les communes) pour situer l'année en cours.
    sev=t.groupby('year')[['swi_jja_z','swi_son_z','rp_max_log']].mean()
    obs=hist.groupby('year').y.sum()
    sev=sev.join(obs.rename('communes_reconnues'))
    rank=int((sev.rp_max_log>=sev.loc[YEAR,'rp_max_log']).sum())
    contours=load_contours(RAW.as_posix())
    dep=cur.merge(contours[['code','departement','region']],left_on='insee',right_on='code').groupby(['departement','region']).agg(expected=('p','sum'),communes=('p','size'),p_mean=('p','mean')).reset_index()
    reg=dep.groupby('region')[['expected','communes']].sum();reg['rate']=reg.expected/reg.communes;region=reg.rate.idxmax()
    maps(cur,contours,dep,region,last_month)
    out={'year':YEAR,'last_month_available':last_month,'sim_file_sha256':digest,'training_years':[FIRST_LABEL_YEAR,mature],'model':KIND,'swi_source':'SWI uniforme krigé au centre des communes','clay_source':'BRGM carte d’exposition 2025, parts de surface communale',
         'expected_recognised_communes':expected,'communes':int(len(cur)),
         'estimation_interval_90':[float(np.quantile(tot,.05)),float(np.quantile(tot,.95))],
         'prediction_interval_80':[float(pi80[0]),float(pi80[1])],'prediction_interval_90':[float(pi90[0]),float(pi90[1])],
         'prediction_interval_loo_coverage':{'80':cov80,'90':cov90,'years':int(len(by))},
         'backtest_ratio_obs_exp_quantiles':{'q10':float(q[0]),'q50':float(q[1]),'q90':float(q[2])},
         'empirical_range':[expected*float(q[0]),expected*float(q[2])],
         'severity':{'rp_max_log_mean':float(sev.loc[YEAR,'rp_max_log']),'swi_jja_z_mean':float(sev.loc[YEAR,'swi_jja_z']),'rank_most_severe':rank,'years_compared':int(sev.rp_max_log.notna().sum())},
         'comparison_years':sev.drop(index=YEAR).sort_values('rp_max_log',ascending=False).head(6).reset_index().to_dict('records'),
         'regions':[{'region':REGIONS[k],'expected':float(v.expected),'rate':float(v.rate)} for k,v in reg.sort_values('rate',ascending=False).iterrows()],
         'top_departements':dep.sort_values('p_mean',ascending=False).head(10).to_dict('records'),'focus_region':REGIONS[region],
         'caveat':'Estimation : les arrêtés de cette année ne sont pas publiés. Le niveau annuel de reconnaissance a varié d’un facteur 0,3 à 15 par rapport au modèle dans le backtest.'}
    (ROOT/'reports/ete_2026.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
    print(json.dumps({k:out[k] for k in ['last_month_available','expected_recognised_communes','backtest_ratio_obs_exp_quantiles','empirical_range','severity','focus_region']},ensure_ascii=False,indent=1,default=float))
    print(pd.DataFrame(out['comparison_years']).round(2).to_string(index=False));print(pd.DataFrame(out['regions']).round(3).to_string(index=False))

def maps(cur,contours,dep,region,last_month):
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    com=contours.merge(cur[['insee','p','rp_max_log']],left_on='code',right_on='insee',how='left')
    fig,axes=plt.subplots(1,2,figsize=(12,6.2))
    com.plot(column='rp_max_log',ax=axes[0],cmap='YlOrBr',vmin=0,vmax=4.5,linewidth=0,legend=True,legend_kwds={'shrink':.6,'label':'ln(période de retour en années)'});axes[0].set_title('Sévérité du SWI uniforme 2026 (jusqu’en septembre)')
    com.plot(column='p',ax=axes[1],cmap='YlOrRd',vmin=0,vmax=1,linewidth=0,legend=True,legend_kwds={'shrink':.6});axes[1].set_title('Probabilité estimée de reconnaissance CatNat')
    for a in axes:a.set_axis_off()
    fig.suptitle(f'Sécheresse 2026 (données Météo-France jusqu’au mois {last_month}) — estimation, arrêtés non publiés');fig.tight_layout();fig.savefig(FIG/'ete_2026_france.png',dpi=110);plt.close(fig)
    d=contours.dissolve(by='departement',as_index=False)[['departement','geometry']].merge(dep,on='departement')
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    d.plot(column='p_mean',ax=axes[0],cmap='YlOrRd',vmin=0,vmax=1,edgecolor='white',linewidth=.3,legend=True,legend_kwds={'shrink':.6});axes[0].set_title('Part attendue de communes reconnues')
    d.plot(column='expected',ax=axes[1],cmap='Reds',edgecolor='white',linewidth=.3,legend=True,legend_kwds={'shrink':.6});axes[1].set_title('Nombre attendu de communes reconnues')
    for a in axes:a.set_axis_off()
    fig.suptitle('Sécheresse 2026 par département (estimation)');fig.tight_layout();fig.savefig(FIG/'ete_2026_departements.png',dpi=110);plt.close(fig)
    r=com[com.region==region];rd=r.dissolve(by='departement',as_index=False)
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    r.plot(column='rp_max_log',ax=axes[0],cmap='YlOrBr',vmin=0,vmax=4.5,linewidth=0,legend=True,legend_kwds={'shrink':.6});axes[0].set_title('Sévérité du SWI uniforme 2026')
    r.plot(column='p',ax=axes[1],cmap='YlOrRd',vmin=0,vmax=1,linewidth=0,legend=True,legend_kwds={'shrink':.6});axes[1].set_title(f'Probabilité estimée (attendu {r.p.sum():.0f} communes)')
    for a in axes:rd.boundary.plot(ax=a,color='#333333',linewidth=.5);a.set_axis_off()
    fig.suptitle(f'{REGIONS[region]} — région la plus exposée en 2026 (estimation)');fig.tight_layout();fig.savefig(FIG/'ete_2026_region.png',dpi=110);plt.close(fig)

if __name__=='__main__':main()
