"""Indicateurs annuels d'humidité des sols par maille, sans information future.

Chaque anomalie standardisée utilise la climatologie du même mois estimée **uniquement sur les années
antérieures** (moyenne et écart-type expansifs) : l'année t n'entre jamais dans sa propre référence."""
import numpy as np
import pandas as pd

FEATURES_METEO=['swi_jja_z','swi_son_z','swi_min_z','sswi3_sep','sswi12_dec','swi_jja_z_prev']
SD_FLOOR=0.02

def _cube(sim,cells,value):
    """Tableau année × maille × mois (NaN si absent)."""
    s=sim.merge(cells[['cell','lambx','lamby']],left_on=['LAMBX','LAMBY'],right_on=['lambx','lamby'])
    years=np.sort(s.year.unique());ids=np.sort(s.cell.unique())
    cube=np.full((len(years),len(ids),12),np.nan)
    yi=np.searchsorted(years,s.year.values);ci=np.searchsorted(ids,s.cell.values)
    cube[yi,ci,s.month.values-1]=s[value].values
    return years,ids,cube

def expanding_anomaly(cube,min_years=5):
    """z[t] = (x[t] − moyenne des années < t) / écart-type des années < t ; NaN avant `min_years` années passées."""
    n=cube.shape[0];z=np.full_like(cube,np.nan)
    cs=np.nancumsum(cube,axis=0);cs2=np.nancumsum(cube**2,axis=0)
    for t in range(min_years,n):
        mean=cs[t-1]/t;var=(cs2[t-1]-t*mean**2)/(t-1)
        z[t]=(cube[t]-mean)/np.maximum(np.sqrt(np.maximum(var,0)),SD_FLOOR)
    return z

def build_features(sim,cells,min_years=5,last_month=12):
    """Une ligne par maille et année, à partir de la (min_years+1)-ième année de la SIM.

    `last_month` < 12 limite tous les indicateurs aux mois connus (prévision en cours d'année) :
    automne = septembre…last_month, minimum = mars…last_month, SSWI12 pris au mois last_month."""
    years,ids,swi=_cube(sim,cells,'SWI')
    swi=swi[:,:,:last_month]
    if np.isnan(swi).any():raise ValueError('SWI manquant : années ou mailles incomplètes dans la SIM mensuelle.')
    _,_,sswi3=_cube(sim,cells,'SSWI3');_,_,sswi12=_cube(sim,cells,'SSWI12')
    z=expanding_anomaly(swi,min_years)
    autumn_end=min(last_month,11)
    jja=z[:,:,5:8].mean(axis=2);son=z[:,:,8:autumn_end].mean(axis=2);zmin=z[:,:,2:autumn_end].min(axis=2)
    prev=np.full_like(jja,np.nan);prev[1:]=jja[:-1]
    cols={'swi_jja_z':jja,'swi_son_z':son,'swi_min_z':zmin,'sswi3_sep':sswi3[:,:,8],'sswi12_dec':sswi12[:,:,last_month-1],'swi_jja_z_prev':prev}
    rows=[]
    # La première année d'anomalie n'a pas d'été précédent standardisé : on commence à min_years+1.
    for k in range(min_years+1,len(years)):
        d={'cell':ids,'year':np.full(len(ids),years[k])};d.update({n:a[k] for n,a in cols.items()});rows.append(pd.DataFrame(d))
    out=pd.concat(rows,ignore_index=True)
    return out

# ---------------------------------------------------------------- SWI uniforme (cible du critère CatNat)
FEATURES_UNIFORM=['swi_jja_z','swi_son_z','swi_min_z','swi_jja_z_prev','rp_max_log']

def build_features_uniform(cube,years,cell_ids,min_years=10,last_month=12,min_ref=20):
    """Indicateurs annuels du SWI **uniforme**, sans information future.

    - anomalies standardisées (été, automne, minimum mensuel) à climatologie expansive ;
    - rp_max_log : log de la plus grande période de retour empirique, parmi les fenêtres glissantes de trois
      mois se terminant de mars à `last_month`, par rapport aux années antérieures (critère de type CatNat).
    `last_month` < 12 limite tous les calculs aux mois connus (estimation en cours d'année)."""
    from .swi import rolling_quarter_means
    from .criterion import return_period
    q=rolling_quarter_means(cube)  # cube complet : seule l'année en cours peut avoir des mois manquants
    cube=cube[:,:,:last_month]
    z=expanding_anomaly(cube,min_years)
    end=min(last_month,11)
    jja=z[:,:,5:8].mean(axis=2);son=z[:,:,8:end].mean(axis=2) if end>8 else np.full_like(jja,np.nan)
    zmin=z[:,:,2:end].min(axis=2)
    prev=np.full_like(jja,np.nan);prev[1:]=jja[:-1]
    rp_max=np.full(jja.shape,np.nan)
    for t in range(min_years+1,len(years)):
        rp=return_period(q,t,min_ref=min_ref)[:,2:last_month]
        rp_max[t]=np.nanmax(rp,axis=1)
    cols={'swi_jja_z':jja,'swi_son_z':son,'swi_min_z':zmin,'swi_jja_z_prev':prev,'rp_max_log':np.log(rp_max)}
    rows=[]
    for k in range(min_years+1,len(years)):
        d={'cell':cell_ids,'year':np.full(len(cell_ids),years[k])};d.update({n:a[k] for n,a in cols.items()});rows.append(pd.DataFrame(d))
    return pd.concat(rows,ignore_index=True)
