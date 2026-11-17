"""Cartes France (communes), départements et zoom régional, à partir des prévisions hors échantillon."""
import numpy as np
import pandas as pd

REGIONS={'11':'Île-de-France','24':'Centre-Val de Loire','27':'Bourgogne-Franche-Comté','28':'Normandie','32':'Hauts-de-France','44':'Grand Est',
         '52':'Pays de la Loire','53':'Bretagne','75':'Nouvelle-Aquitaine','76':'Occitanie','84':'Auvergne-Rhône-Alpes','93':"Provence-Alpes-Côte d'Azur",'94':'Corse'}
MODEL='p_glm_complet'

def load_contours(raw):
    import geopandas as gpd
    g=gpd.read_file(f'/vsigzip/{raw}/communes-100m.geojson.gz')
    g=g[g.region.isin(REGIONS)][['code','nom','departement','region','geometry']].to_crs(2154)
    # Contours simplifiés à 100 m : quelques polygones deviennent invalides après reprojection ; on les répare avant fusion.
    g['geometry']=g.geometry.make_valid()
    return g

def commune_summary(pred,model=MODEL):
    return pred.groupby('insee').agg(observed=('y','mean'),predicted=(model,'mean'),years=('y','size')).reset_index()

def department_summary(pred,contours,model=MODEL):
    d=pred.merge(contours[['code','departement','region']],left_on='insee',right_on='code')
    g=d.groupby('departement').agg(region=('region','first'),observed=('y','sum'),expected=(model,'sum'),commune_years=('y','size')).reset_index()
    g['observed_rate']=g.observed/g.commune_years;g['expected_rate']=g.expected/g.commune_years;g['ratio_obs_exp']=g.observed/g.expected
    return g

def choose_region(dep):
    """Région la plus touchée : plus forte fréquence observée de reconnaissance sur la période de test."""
    r=dep.groupby('region')[['observed','commune_years']].sum();r['rate']=r.observed/r.commune_years
    return r.rate.idxmax(),r.sort_values('rate',ascending=False)

def make_maps(pred,raw,fig_dir,model=MODEL):
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm,TwoSlopeNorm
    contours=load_contours(raw)
    com=contours.merge(commune_summary(pred,model),left_on='code',right_on='insee',how='left')
    vmax=float(np.nanquantile(com[['observed','predicted']].to_numpy(),0.99))
    fig,axes=plt.subplots(1,2,figsize=(12,6.2))
    for ax,col,title in zip(axes,['observed','predicted'],['Fréquence observée','Fréquence prédite (GLM, hors échantillon)']):
        com.plot(column=col,ax=ax,cmap='YlOrRd',vmin=0,vmax=vmax,linewidth=0,legend=True,legend_kwds={'shrink':.6},missing_kwds={'color':'#eeeeee'})
        ax.set_title(title);ax.set_axis_off()
    y0,y1=int(pred.year.min()),int(pred.year.max())
    fig.suptitle(f'Reconnaissance CatNat sécheresse par commune, part des années {y0}–{y1}');fig.tight_layout();fig.savefig(fig_dir/'carte_france_communes.png',dpi=110);plt.close(fig)
    dep=department_summary(pred,contours,model);dep.to_csv(fig_dir.parent/'departements.csv',index=False)
    dshape=contours.dissolve(by='departement',as_index=False)[['departement','geometry']].merge(dep,on='departement')
    fig,axes=plt.subplots(1,3,figsize=(16,5.8))
    vmax=float(dshape[['observed_rate','expected_rate']].max().max())
    for ax,col,title in zip(axes[:2],['observed_rate','expected_rate'],['Fréquence observée','Fréquence prédite']):
        dshape.plot(column=col,ax=ax,cmap='YlOrRd',vmin=0,vmax=vmax,edgecolor='white',linewidth=.3,legend=True,legend_kwds={'shrink':.6});ax.set_title(title);ax.set_axis_off()
    dshape.plot(column='ratio_obs_exp',ax=axes[2],cmap='RdBu_r',norm=LogNorm(vmin=0.25,vmax=4),edgecolor='white',linewidth=.3,legend=True,legend_kwds={'shrink':.6})
    axes[2].set_title('Observé / attendu (>1 : sous-estimation)');axes[2].set_axis_off()
    fig.suptitle(f'Départements, {y0}–{y1}');fig.tight_layout();fig.savefig(fig_dir/'carte_departements.png',dpi=110);plt.close(fig)
    code,ranking=choose_region(dep);name=REGIONS[code]
    reg=contours[contours.region==code]
    rp=pred[pred.insee.isin(reg.code)]
    year=int(rp.groupby('year').y.sum().idxmax())
    ry=reg.merge(rp[rp.year==year][['insee','y',model]],left_on='code',right_on='insee',how='left')
    rc=reg.merge(commune_summary(rp,model),left_on='code',right_on='insee',how='left')
    rdep=reg.dissolve(by='departement',as_index=False)
    fig,axes=plt.subplots(1,3,figsize=(17,6))
    rc.plot(column='observed',ax=axes[0],cmap='YlOrRd',linewidth=0,legend=True,legend_kwds={'shrink':.6})
    axes[0].set_title(f'Fréquence observée {y0}–{y1}')
    ry.plot(column='y',ax=axes[1],categorical=True,cmap='Reds',linewidth=0,legend=True,legend_kwds={'labels':['non reconnue','reconnue'],'loc':'lower left'})
    axes[1].set_title(f'{year} : communes reconnues ({int(ry.y.sum())})')
    ry.plot(column=model,ax=axes[2],cmap='YlOrRd',vmin=0,vmax=1,linewidth=0,legend=True,legend_kwds={'shrink':.6})
    axes[2].set_title(f'{year} : probabilité prédite (attendu {ry[model].sum():.0f})')
    for ax in axes:rdep.boundary.plot(ax=ax,color='#333333',linewidth=.5);ax.set_axis_off()
    fig.suptitle(f'{name} — région la plus touchée sur la période');fig.tight_layout();fig.savefig(fig_dir/f'carte_region_{code}.png',dpi=110);plt.close(fig)
    return {'region_code':code,'region':name,'region_year':year,'region_observed':int(ry.y.sum()),'region_expected':float(ry[model].sum()),
            'region_ranking':[{'region':REGIONS[k],'rate':float(v)} for k,v in ranking.rate.items()],
            'departments_file':'reports/departements.csv'}
