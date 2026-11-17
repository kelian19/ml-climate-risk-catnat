import numpy as np
import pandas as pd
import pytest
from catnat.uncertainty import bootstrap_probabilities,quantile_bands,ratio_interval,loo_year_coverage
from catnat.model import make_estimator

def table(n_years=16,n=400,seed=0):
    rng=np.random.default_rng(seed);rows=[]
    for yr in range(2000,2000+n_years):
        shock=rng.normal()
        for c in range(n):
            x=rng.normal()+shock;p=1/(1+np.exp(-(-2.5+1.0*x)));rows.append({'insee':f'{c:05d}','year':yr,'y':int(rng.uniform()<p),'swi_jja_z':x})
    return pd.DataFrame(rows)

def test_bootstrap_bands_are_ordered_wider_with_fewer_years_and_cover_the_truth():
    t=table(16);train=t[t.year<2014];target=t[t.year==2014].reset_index(drop=True);cols=['swi_jja_z']
    mk=lambda:make_estimator('glm_meteo')
    d=bootstrap_probabilities(train,target,cols,mk,n_boot=60,seed=1,commune_fraction=1.0)
    lo,hi=quantile_bands(d,0.9);assert (lo<=hi).all() and d.shape==(60,len(target))
    truth=1/(1+np.exp(-(-2.5+1.0*target.swi_jja_z.to_numpy())))
    assert np.mean((truth>=lo-0.02)&(truth<=hi+0.02))>0.7
    short=bootstrap_probabilities(train[train.year<2006],target,cols,mk,n_boot=60,seed=1,commune_fraction=1.0)
    w_long=np.mean(quantile_bands(d)[1]-quantile_bands(d)[0]);w_short=np.mean(quantile_bands(short)[1]-quantile_bands(short)[0])
    assert w_short>w_long

def test_bootstrap_is_reproducible():
    t=table(12);tr=t[t.year<10+2000];tg=t[t.year==2010].reset_index(drop=True);mk=lambda:make_estimator('glm_meteo')
    a=bootstrap_probabilities(tr,tg,['swi_jja_z'],mk,n_boot=10,seed=3,commune_fraction=1.0);b=bootstrap_probabilities(tr,tg,['swi_jja_z'],mk,n_boot=10,seed=3,commune_fraction=1.0)
    np.testing.assert_array_equal(a,b)

def test_ratio_interval_and_loo_coverage_match_nominal_level_on_lognormal_noise():
    rng=np.random.default_rng(0);n=400;expected=rng.uniform(500,3000,size=n);ratio=np.exp(rng.normal(0,0.6,size=n))
    by=pd.DataFrame({'year':np.arange(n),'expected':expected,'observed':expected*ratio})
    cov,tab=loo_year_coverage(by,0.8);assert 0.74<cov<0.86 and tab.covered.mean()==cov
    lo,hi=ratio_interval(ratio,1000.,0.8);assert lo<1000*np.median(ratio)<hi
