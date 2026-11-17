import numpy as np
import pandas as pd
import pytest
from catnat.features import expanding_anomaly,build_features,FEATURES_METEO
from catnat.labels import last_mature_year,build_labels,history_counts
from catnat.model import rolling_origin,credibility_frequency,FEATURE_SETS
from catnat.metrics import log_loss,brier,scores,by_year,calibration_table
from catnat.data import load_events,load_rga

def events_frame(rows):
    return pd.DataFrame(rows,columns=['insee','start','end','published']).assign(peril='Sécheresse').astype({'start':'datetime64[ns]','end':'datetime64[ns]','published':'datetime64[ns]'})

# ---------- anomalies sans information future
def test_expanding_anomaly_uses_only_past_years():
    rng=np.random.default_rng(0);cube=rng.normal(size=(9,3,12))
    z=expanding_anomaly(cube,min_years=5)
    assert np.isnan(z[:5]).all()
    t=6;mean=cube[:t].mean(axis=0);sd=cube[:t].std(axis=0,ddof=1)
    np.testing.assert_allclose(z[t],(cube[t]-mean)/sd)
    changed=cube.copy();changed[8]+=100
    np.testing.assert_allclose(expanding_anomaly(changed,5)[:8],z[:8],equal_nan=True)

def synthetic_sim(n_years=8,cells=((600,24010),(760,24010))):
    rows=[]
    for k,(x,y) in enumerate(cells):
        for yr in range(2000,2000+n_years):
            for m in range(1,13):rows.append({'LAMBX':x,'LAMBY':y,'year':yr,'month':m,'SWI':0.5+0.3*np.sin(m)+0.01*yr%7+0.05*k,'SSWI3':-0.1*k,'SSWI12':0.2})
    cellsdf=pd.DataFrame({'cell':[10,20],'lambx':[c[0] for c in cells],'lamby':[c[1] for c in cells]})
    return pd.DataFrame(rows),cellsdf

def test_build_features_shape_and_no_future_leakage():
    sim,cells=synthetic_sim()
    f=build_features(sim,cells,min_years=5)
    assert sorted(f.year.unique())==[2006,2007] and len(f)==4 and not f[FEATURES_METEO].isna().any().any()
    sim2=sim.copy();sim2.loc[sim2.year==2007,'SWI']+=1
    g=build_features(sim2,cells,min_years=5)
    pd.testing.assert_frame_equal(f[f.year<2007].reset_index(drop=True),g[g.year<2007].reset_index(drop=True))
    assert (g[g.year==2007].swi_jja_z>f[f.year==2007].swi_jja_z).all()

def test_build_features_refuses_missing_months():
    sim,cells=synthetic_sim();sim=sim.drop(index=3)
    with pytest.raises(ValueError,match='manquant'):build_features(sim,cells)

# ---------- variable à expliquer et maturité
def test_labels_count_event_start_year_and_complete_grid():
    communes=pd.DataFrame({'code':['01001','01002']})
    ev=events_frame([['01001','2018-07-01','2018-09-30','2019-06-01'],['01001','2018-10-01','2018-12-31','2019-07-01'],['01002','2019-04-01','2019-06-30','2020-05-01'],['99999','2019-01-01','2019-03-31','2020-01-01']])
    lab=build_labels(ev,communes,[2018,2019,2020])
    assert len(lab)==6
    row=lab.set_index(['insee','year'])
    assert row.loc[('01001',2018),'n_arretes']==2 and row.loc[('01001',2018),'y']==1
    assert row.loc[('01002',2019),'y']==1 and row.loc[('01002',2020),'y']==0 and lab.y.sum()==2

def test_history_counts_only_use_published_information():
    communes=pd.DataFrame({'code':['01001']})
    ev=events_frame([['01001','2015-07-01','2015-09-30','2016-06-01'],['01001','2017-07-01','2017-09-30','2019-03-01']])
    h=history_counts(ev,communes,[2016,2017,2018,2019,2020]).set_index('year').hist_count
    assert 2016 not in h.index
    assert h[2017]==1 and h[2018]==1 and h[2019]==1 and h[2020]==2

def test_last_mature_year_respects_publication_lag():
    rows=[]
    for y in range(2010,2024):
        for k in range(20):rows.append(['01001',f'{y}-07-01',f'{y}-09-30',str((pd.Timestamp(f'{y}-09-30')+pd.Timedelta(days=200+20*k)).date())])
    ev=events_frame(rows)
    # Retard max ≈ 1,6 an ; dernière publication ≈ mai 2025 → 2022 mûre, 2023 non.
    assert last_mature_year(ev)==2022

# ---------- validation temporelle
def synthetic_table(seed=0):
    rng=np.random.default_rng(seed);rows=[]
    for yr in range(2005,2016):
        shock=rng.normal()
        for c in range(300):
            x={f:rng.normal() for f in FEATURES_METEO};x['swi_jja_z']+=shock
            ex={'rga_mid_share':rng.uniform(),'rga_high_share':rng.uniform()*0.3,'rga_missing':0,'log_population':rng.uniform(4,9),'hist_count':rng.integers(0,4)}
            logit=-2.5-1.2*x['swi_jja_z']+2*ex['rga_high_share']
            y=int(rng.uniform()<1/(1+np.exp(-logit)))
            rows.append({'insee':f'{c:05d}','year':yr,'y':y,'n_arretes':y,'population':100,**x,**ex})
    return pd.DataFrame(rows)

def test_rolling_origin_trains_only_on_lagged_years_and_is_blind_to_test_labels():
    t=synthetic_table()
    pred,_=rolling_origin(t,[2012,2013],kinds=('glm_meteo',),label_lag=2)
    assert set(pred.year)=={2012,2013}
    assert pred[pred.year==2012].train_years.iloc[0]=='2005–2010'
    t2=t.copy();t2.loc[t2.year>=2011,'y']=1-t2.loc[t2.year>=2011,'y']
    pred2,_=rolling_origin(t2,[2012],kinds=('glm_meteo',),label_lag=2)
    np.testing.assert_allclose(pred[pred.year==2012].p_glm_meteo.values,pred2.p_glm_meteo.values)

def test_glm_beats_constant_on_a_learnable_signal():
    t=synthetic_table();pred,_=rolling_origin(t,[2013,2014,2015],kinds=('glm_meteo_expo',))
    s=scores(pred.y,pred.p_glm_meteo_expo,reference=pred.p_constante)
    assert s['log_loss_skill']>0.05 and s['auc']>0.7

def test_rolling_origin_refuses_short_history():
    with pytest.raises(ValueError,match='moins de'):rolling_origin(synthetic_table(),[2007],kinds=('glm_meteo',))

def test_credibility_frequency_formula():
    train=pd.DataFrame({'insee':['a']*4+['b']*4,'y':[1,1,0,0,0,0,0,0]});test=pd.DataFrame({'insee':['a','b','c']})
    p=credibility_frequency(train,test,k=3)
    pbar=0.25
    np.testing.assert_allclose(p,[(2+3*pbar)/7,(0+3*pbar)/7,pbar])

# ---------- mesures
def test_metrics_reference_values():
    y=np.array([0,1,1,0]);p=np.array([.2,.8,.6,.4])
    assert log_loss(y,p)==pytest.approx(-np.mean(np.log([.8,.8,.6,.6])))
    assert brier(y,p)==pytest.approx(np.mean([.04,.04,.16,.16]))
    s=scores(y,p,reference=np.full(4,.5));assert s['auc']==1 and s['log_loss_skill']>0 and s['observed']==2
    pred=pd.DataFrame({'year':[1,1,2],'y':[1,0,1],'p':[.5,.5,.25]})
    b=by_year(pred,'p').set_index('year');assert b.loc[1,'ratio_obs_exp']==1 and b.loc[2,'ratio_obs_exp']==4
    assert calibration_table(np.r_[y,y],np.r_[p,p],bins=2).n.sum()==8

# ---------- lecture des sources (formats réels, fichiers réduits)
def test_load_events_reads_headerless_semicolon_file(tmp_path):
    (tmp_path/'catnat.csv').write_text("1;04054;Ch;200067437;CA;04;AHP;93;;;;;Sécheresse;2017-07-01 00:00:00.000;2017-09-30 00:00:00.000;2018-06-27 00:00:00.000\n2;4055;Ch;200068625;CC;04;AHP;93;;;;;Inondations;1996-01-11 00:00:00.000;1996-01-12 00:00:00.000;1996-06-17 00:00:00.000\n",encoding='utf-8')
    ev=load_events(tmp_path)
    assert len(ev)==1 and ev.insee[0]=='04054' and ev.start[0]==pd.Timestamp('2017-07-01')

def test_load_rga_share_uses_epci_area_and_keeps_secret_values_missing(tmp_path):
    (tmp_path/'rga_epci.csv').write_text('EPCI_CODE,EPCI_LIBELLE,INDICATEUR_EXPOSITION,VALEUR_EXPOSITION\n1,A,Surface_exposee_RGA2_km2,50\n1,A,Surface_exposee_RGA3_km2,25\n2,B,Surface_exposee_RGA2_km2,\n2,B,Surface_exposee_RGA3_km2,10\n',encoding='utf-8')
    communes=pd.DataFrame({'codeEpci':['1','1','2'],'surface_km2':[60.,40.,20.]})
    r=load_rga(tmp_path,communes).set_index('codeEpci')
    assert r.loc['1','rga_mid_share']==0.5 and r.loc['1','rga_high_share']==0.25
    assert np.isnan(r.loc['2','rga_mid_share']) and r.loc['2','rga_high_share']==0.5
