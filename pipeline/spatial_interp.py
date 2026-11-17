"""Estimer le SWI uniforme là où il n'existe pas : krigeage vers les centres de communes.

Le SWI uniforme n'existe qu'aux 8 981 mailles Safran (≈ 8 km). Une commune est entre mailles : on estime son SWI par
krigeage ordinaire (poids calculés une fois, appliqués à toute la série mensuelle), avec variance de krigeage, au lieu
de prendre la maille la plus proche.

1. variogramme standardisé médian (champs d'été standardisés, 1959-2025) ;
2. validation en retirant 10 % des mailles au hasard : plus proche voisin, IDW et krigeage, sur 67 étés ;
3. série mensuelle au centre de chaque commune (data/processed/swi_commune.npz) ;
4. effet sur le modèle de fréquence : indicateurs de la maille la plus proche contre indicateurs krigés.

python -m pipeline.spatial_interp
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from catnat.swi import load_cube
from catnat.data import load_communes
from catnat.geostat import empirical_variogram,fit_variogram,kriging_weights,apply_weights
from catnat.features import build_features_uniform,FEATURES_UNIFORM
from catnat.model import rolling_origin,FEATURE_SETS
from catnat.metrics import scores
ROOT=Path(__file__).resolve().parents[1]

def standardized_variogram(summer,xy,years,model='exponentiel',max_dist=100000.):
    """Paramètres médians (pépite, palier = 1 − pépite, portée) du variogramme de champs d'été standardisés.

    Modèle exponentiel ajusté sur les distances < 100 km : choisi par validation (RMSE 0,0358 contre 0,0391 pour un ajustement
    sphérique sur 400 km), car l'interpolation à 3-8 km dépend du comportement aux petites distances."""
    rows=[]
    for t in range(len(years)):
        z=summer[t]
        if not np.isfinite(z).all():continue
        z=(z-z.mean())/z.std(ddof=1);lag,gam,cnt=empirical_variogram(xy,z,max_dist,25,max_pairs=200000,seed=int(years[t]))
        f=fit_variogram(lag,gam,cnt,model);tot=f['nugget']+f['psill'];rows.append({'year':int(years[t]),'nugget_ratio':f['nugget']/tot,'range':f['range']})
    d=pd.DataFrame(rows);r=float(d.nugget_ratio.median())
    return {'model':model,'nugget':r,'psill':1.-r,'range':float(d.range.median())},d

def idw_weights(xy_obs,xy_new,k=8,power=2.):
    tree=cKDTree(xy_obs);d,nn=tree.query(xy_new,k=k);d=np.maximum(d,1.);w=1./d**power;return nn,w/w.sum(axis=1,keepdims=True)

def holdout_validation(summer,xy,years,params,frac=0.10,seed=0,n_neighbors=24):
    rng=np.random.default_rng(seed);n=len(xy);test=np.sort(rng.choice(n,int(frac*n),replace=False));obs=np.setdiff1d(np.arange(n),test)
    nnK,WK,varK=kriging_weights(xy[obs],xy[test],params,n_neighbors);nnI,WI=idw_weights(xy[obs],xy[test]);nnN=cKDTree(xy[obs]).query(xy[test],k=1)[1]
    dist=cKDTree(xy[obs]).query(xy[test],k=1)[0]
    res={'NN':[],'IDW':[],'KRIG':[]};cover=[];zs=[]
    for t in range(len(years)):
        z=summer[t]
        if not np.isfinite(z).all():continue
        zo=z[obs];zt=z[test];var_field=z.var(ddof=1)
        pN=zo[nnN];pI=np.einsum('ik,ik->i',WI,zo[nnI]);pK=np.einsum('ik,ik->i',WK,zo[nnK])
        for k,p in (('NN',pN),('IDW',pI),('KRIG',pK)):res[k].append(p-zt)
        sd=np.sqrt(varK*var_field);cover.append(np.abs(pK-zt)<=1.96*sd);zs.append((pK-zt)/np.maximum(sd,1e-9))
    out={}
    for k,v in res.items():
        e=np.concatenate(v);out[k]={'rmse':float(np.sqrt(np.mean(e**2))),'mae':float(np.mean(np.abs(e))),'bias':float(e.mean())}
    out['KRIG']['coverage_95']=float(np.concatenate(cover).mean());out['KRIG']['std_standardized_error']=float(np.concatenate(zs).std())
    out['n_test_cells']=int(len(test));out['n_years']=int(len(res['NN']));out['median_distance_to_nearest_obs_km']=float(np.median(dist)/1000)
    return out

def main():
    years,ids,cube,grid=load_cube();xy=grid[['x93','y93']].to_numpy(float);summer=cube[:,:,5:8].mean(axis=2)
    params,per_year=standardized_variogram(summer,xy,years);print('variogramme standardisé',params,flush=True)
    val=holdout_validation(summer,xy,years,params);print(json.dumps(val,indent=1),flush=True)
    com=load_communes();tr=Transformer.from_crs(4326,2154,always_xy=True);cx,cy=tr.transform(com.lon.values,com.lat.values);cxy=np.c_[cx,cy]
    nn,W,var=kriging_weights(xy,cxy,params,24);dist,nearest=cKDTree(xy).query(cxy)
    out_cube=np.empty((cube.shape[0],len(com),12),dtype=np.float32)
    for t in range(cube.shape[0]):out_cube[t]=np.einsum('ikm,ik->im',cube[t][nn],W)
    np.savez_compressed(ROOT/'data/processed/swi_commune.npz',years=years,codes=com.code.values,cube=out_cube,krig_var=var.astype(np.float32),nearest_cell=ids[nearest])
    nn_cube=cube[:,nearest,:]
    diff=(out_cube[:,:,5:8].mean(axis=2)-nn_cube[:,:,5:8].mean(axis=2));fin=np.isfinite(diff)
    info={'standardized_variogram':params,'variogram_by_year':per_year.describe().round(4).to_dict(),'holdout_validation':val,
          'communes':int(len(com)),'median_distance_commune_to_nearest_cell_km':float(np.median(dist)/1000),'p95_distance_km':float(np.quantile(dist,.95)/1000),
          'kriging_variance_normalized':{'median':float(np.median(var)),'p95':float(np.quantile(var,.95))},
          'kriged_minus_nearest_summer_rmse':float(np.sqrt(np.nanmean(diff[fin]**2)))}
    # Effet sur le modèle de fréquence : indicateurs krigés contre plus proche maille.
    table=pd.read_parquet(ROOT/'data/processed/commune_year.parquet');mature=int(table.year.max());keep=years<=mature
    feats=build_features_uniform(out_cube[keep].astype(float),years[keep],com.code.values,10);feats=feats.rename(columns={'cell':'insee'})
    tk=table.drop(columns=FEATURES_UNIFORM).merge(feats,on=['insee','year'],how='left');assert not tk[FEATURES_UNIFORM].isna().any().any()
    test_years=list(range(1995,mature+1));res={}
    for name,t in (('plus_proche_maille',table),('krigeage',tk)):
        pred,_=rolling_origin(t,test_years,kinds=('glm_complet',));base=pred.p_constante;p=pred.p_glm_complet
        res[name]=scores(pred.y,p,reference=base)
    info['model_effect']=res;(ROOT/'reports/spatial_interp.json').write_text(json.dumps(info,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
    print(json.dumps({'model_effect':res,'kriged_minus_nearest_summer_rmse':info['kriged_minus_nearest_summer_rmse']},indent=1,default=float))

if __name__=='__main__':main()
