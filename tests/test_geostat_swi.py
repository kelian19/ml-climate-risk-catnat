import numpy as np
import pandas as pd
import pytest
from catnat.geostat import knn_weights,morans_i,empirical_variogram,fit_variogram,spherical,exponential,ordinary_kriging,block_cv_kriging
from catnat.swi import to_cube,rolling_quarter_means
from catnat.criterion import thresholds,criterion_cube,return_period
from catnat.forecast import predictor_table,rolling_forecast,forecast_scores

def gaussian_field(n=900,range_=40000.,sill=1.,nugget=0.05,seed=0):
    """Champ gaussien à covariance exponentielle connue sur un semis de points (m)."""
    rng=np.random.default_rng(seed);xy=rng.uniform(0,200000,size=(n,2))
    d=np.linalg.norm(xy[:,None]-xy[None],axis=2);C=sill*np.exp(-3*d/range_)+nugget*np.eye(n)
    z=np.linalg.cholesky(C+1e-9*np.eye(n))@rng.standard_normal(n)
    return xy,z

def test_variogram_fit_recovers_known_parameters():
    xy,z=gaussian_field()
    lag,gam,cnt=empirical_variogram(xy,z,max_dist=100000.,bins=16)
    p=fit_variogram(lag,gam,cnt,'exponentiel')
    assert p['range']==pytest.approx(40000.,rel=0.45) and p['psill']==pytest.approx(1.,rel=0.5) and p['nugget']<0.4

def test_models_basic_properties():
    h=np.array([0.,50.,1000.])
    assert spherical(h,0.1,1.,100.)[2]==pytest.approx(1.1) and spherical(h,0.1,1.,100.)[0]==pytest.approx(0.1)
    assert exponential(h,0.,1.,100.)[2]>0.99

def test_morans_i_detects_spatial_structure_and_noise():
    xy,z=gaussian_field(400);idx,w=knn_weights(xy,8)
    i,ei,p=morans_i(z,idx,w,permutations=99);assert i>0.25 and p<0.05 and ei<0
    noise=np.random.default_rng(1).standard_normal(400);i2,_,p2=morans_i(noise,idx,w,permutations=99)
    assert abs(i2)<0.15 and p2>0.05

def test_kriging_interpolates_exactly_without_nugget_and_has_small_variance_near_data():
    xy,z=gaussian_field(300,nugget=1e-6);params={'model':'exponentiel','nugget':0.,'psill':1.,'range':40000.}
    p,v=ordinary_kriging(xy,z,xy[:20],params,n_neighbors=16)
    np.testing.assert_allclose(p,z[:20],atol=1e-3);assert v.max()<1e-4
    far=np.array([[1e7,1e7]]);_,vfar=ordinary_kriging(xy,z,far,params,16)
    assert vfar[0]>0.5

def test_block_cv_is_honest_about_error_and_calibrated_coverage():
    xy,z=gaussian_field(700,nugget=0.05);lag,gam,cnt=empirical_variogram(xy,z,100000.,16);p=fit_variogram(lag,gam,cnt,'exponentiel')
    r=block_cv_kriging(xy,z,p,block_km=25.,n_neighbors=20,max_blocks=8)
    assert r['n']>50 and r['rmse']<np.std(z) and 0.7<r['coverage_95']<1.0

# ---------- SWI uniforme et critère
def long_frame():
    rows=[]
    for c in (1,2):
        for y in range(1960,1964):
            for m in range(1,13):rows.append({'cell':c,'year':y,'month':m,'swi':0.1*m+0.01*c})
    return pd.DataFrame(rows)

def test_cube_layout_and_rolling_quarters_cross_year_boundary():
    years,ids,cube=to_cube(long_frame(),[1,2],first_year=1960,last_year=1963)
    assert cube.shape==(4,2,12) and cube[0,0,0]==pytest.approx(0.11)
    q=rolling_quarter_means(cube)
    assert np.isnan(q[0,:,:2]).all()
    assert q[1,0,0]==pytest.approx(np.mean([cube[0,0,10],cube[0,0,11],cube[1,0,0]]))
    assert q[0,0,2]==pytest.approx(np.mean(cube[0,0,0:3]))

def test_threshold_and_return_period_use_only_past_years():
    rng=np.random.default_rng(0);q=rng.normal(size=(60,3,12))
    thr=thresholds(q,50,T=25,min_ref=30);np.testing.assert_allclose(thr,np.quantile(q[:50],1/25,axis=0))
    changed=q.copy();changed[55:]-=10
    np.testing.assert_allclose(thresholds(changed,50,25,30),thr);assert np.isnan(thresholds(q,10,25,30)).all()
    low=q.copy();low[55]=-10;rp=return_period(low,55);assert (rp>40).all()
    met,valid=criterion_cube(low,T=25,min_ref=30);assert met[55].all() and not met[:30].any()

# ---------- prévision
def synthetic_cube(years=40,cells=30,seed=0):
    rng=np.random.default_rng(seed);base=rng.normal(size=(years,1,1))*0.1+0.6;seas=0.3*np.cos((np.arange(12)-0)/12*2*np.pi)[None,None]
    return np.clip(base+seas+rng.normal(scale=0.05,size=(years,cells,12)),0,1.4)

def test_rolling_forecast_never_uses_target_year_and_beats_climatology_when_memory_exists():
    cube=synthetic_cube();years=np.arange(1959,1999);tab=predictor_table(cube,years,np.arange(30))
    pred=rolling_forecast(tab,[1990,1995],kinds=('ridge',),min_train_years=15)
    assert set(pred.year)=={1990,1995}
    tab2=tab.copy();tab2.loc[tab2.year>=1990,'target']+=5
    pred2=rolling_forecast(tab2,[1990],kinds=('ridge',),min_train_years=15)
    np.testing.assert_allclose(pred[pred.year==1990].p_ridge.values,pred2.p_ridge.values)
    s=forecast_scores(pred,['p_ridge','p_climatologie']).set_index('model')
    assert s.loc['p_ridge','rmse']<=s.loc['p_climatologie','rmse']*1.05

def test_rolling_forecast_refuses_short_history():
    cube=synthetic_cube(20);tab=predictor_table(cube,np.arange(1959,1979),np.arange(30))
    with pytest.raises(ValueError,match='moins de'):rolling_forecast(tab,[1965],kinds=('ridge',),min_train_years=15)

# ---------- indicateurs du SWI uniforme
def test_uniform_features_are_causal_and_support_partial_year():
    from catnat.features import build_features_uniform,FEATURES_UNIFORM
    cube=synthetic_cube(45,6,seed=1);years=np.arange(1959,2004);ids=np.arange(6)
    f=build_features_uniform(cube,years,ids,min_years=10,last_month=12,min_ref=10)
    assert f.year.min()==1970 and not f[FEATURES_UNIFORM].isna().any().any()
    changed=cube.copy();changed[-1]-=1.0
    g=build_features_uniform(changed,years,ids,min_years=10,last_month=12,min_ref=10)
    pd.testing.assert_frame_equal(f[f.year<2003].reset_index(drop=True),g[g.year<2003].reset_index(drop=True))
    assert (g[g.year==2003].rp_max_log>=f[f.year==2003].rp_max_log).all()
    partial=cube.copy();partial[-1,:,9:]=np.nan
    p=build_features_uniform(partial,years,ids,min_years=10,last_month=9,min_ref=10)
    assert not p[FEATURES_UNIFORM].isna().any().any()
    pd.testing.assert_frame_equal(p[p.year<2003].reset_index(drop=True),build_features_uniform(cube,years,ids,10,9,10).query('year<2003').reset_index(drop=True))

def test_uniform_return_period_rises_in_a_dry_year():
    from catnat.features import build_features_uniform
    cube=synthetic_cube(45,6,seed=2);years=np.arange(1959,2004);dry=cube.copy();dry[-1]-=0.4
    a=build_features_uniform(cube,years,np.arange(6),10,12,10);b=build_features_uniform(dry,years,np.arange(6),10,12,10)
    assert b[b.year==2003].rp_max_log.mean()>a[a.year==2003].rp_max_log.mean()+0.5

# ---------- tendances climatiques
def test_theil_sen_recovers_a_known_trend_and_mann_kendall_detects_it():
    from catnat.climate import theil_sen_trend,severe_summer_frequency,national_trend_per_decade,decade_table
    yrs=np.arange(1959,2027).astype(float);rng=np.random.default_rng(0);s=0.6-0.004*(yrs-1959)+rng.normal(0,0.02,len(yrs))
    slope,p=theil_sen_trend(s,yrs);assert slope==pytest.approx(-0.004,abs=0.0008) and p<0.001
    flat=rng.normal(0.6,0.05,len(yrs));assert theil_sen_trend(flat,yrs)[1]>0.01
    cube=np.repeat((0.6-0.004*(yrs-1959))[:,None,None],5,axis=1)+rng.normal(0,0.02,(len(yrs),5,12));summer=cube[:,:,5:8].mean(axis=2)
    nat=national_trend_per_decade(summer,yrs.astype(int));assert nat['ci90'][0]<-0.02<nat['ci90'][1]+0.04 and nat['per_decade']==pytest.approx(-0.04,abs=0.01)
    f=severe_summer_frequency(summer,yrs.astype(int));d=decade_table(f,yrs.astype(int))
    assert f[(yrs>=1959)&(yrs<=1988)].mean()==pytest.approx(0.10,abs=0.05) and d[-1]['severe_share']>d[0]['severe_share']

def test_kriging_weights_sum_to_one_reproduce_constants_and_match_ordinary_kriging():
    from catnat.geostat import kriging_weights,apply_weights
    xy,z=gaussian_field(300,nugget=0.05);params={'model':'exponentiel','nugget':0.05,'psill':1.,'range':40000.}
    rng=np.random.default_rng(1);new=rng.uniform(20000,180000,size=(25,2))
    nn,W,var=kriging_weights(xy,new,params,n_neighbors=16)
    np.testing.assert_allclose(W.sum(axis=1),1.,atol=1e-9);assert (var>=0).all()
    np.testing.assert_allclose(apply_weights(np.full(len(xy),7.3),nn,W),7.3,atol=1e-9)
    p,v=ordinary_kriging(xy,z,new,params,16);np.testing.assert_allclose(apply_weights(z,nn,W),p);np.testing.assert_allclose(v,var)
    series=np.stack([z,2*z+1],axis=0);out=apply_weights(series,nn,W);np.testing.assert_allclose(out[1],2*out[0]+1,atol=1e-9)
    nan_series=z.copy();nan_series[nn[0,0]]=np.nan;assert np.isnan(apply_weights(nan_series,nn,W)[0])
