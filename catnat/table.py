"""Assemblage de la table commune × année utilisée par les modèles."""
import numpy as np
from .data import RAW,load_cells,load_communes,assign_cells,load_sim,load_events,load_rga
from .features import build_features,build_features_uniform,FEATURES_UNIFORM,FEATURES_METEO
from .swi import load_cube
from .labels import last_mature_year,build_labels,history_counts

# 1958 est partiel (août–décembre) ; les arrêtés sécheresse commencent en 1988-1989.
FIRST_SIM_YEAR=1959
FIRST_LABEL_YEAR=1989
CLIMATOLOGY_MIN_YEARS=10

def build_table(raw=RAW,min_years=CLIMATOLOGY_MIN_YEARS,first_sim_year=FIRST_SIM_YEAR,first_label_year=FIRST_LABEL_YEAR,source='uniform'):
    """source='uniform' : SWI uniforme (critère CatNat, par défaut) ; 'sim' : SWI/SSWI du modèle SIM à sols réels."""
    if source=='uniform':years_u,ids_u,cube,grid=load_cube(raw);cells=grid[['cell','lon','lat']]
    else:cells=load_cells(raw)
    communes=assign_cells(load_communes(raw),cells)
    events=load_events(raw);mature=last_mature_year(events)
    if source=='uniform':
        keep=years_u<=mature;feats=build_features_uniform(cube[keep],years_u[keep],ids_u,min_years)
        meteo=FEATURES_UNIFORM
    else:
        feats=build_features(load_sim(range(first_sim_year,mature+1),raw),cells,min_years);meteo=FEATURES_METEO
    years=sorted(int(y) for y in feats.year.unique() if first_label_year<=y<=mature)
    t=build_labels(events,communes,years)
    t=t.merge(communes[['code','nom','codeDepartement','codeEpci','population','cell','cell_distance_km']],left_on='insee',right_on='code').drop(columns='code')
    t=t.merge(feats,on=['cell','year'],how='left')
    t=t.merge(history_counts(events,communes,years),on=['insee','year'],how='left')
    t['hist_count']=t.hist_count.fillna(0)
    t=t.merge(load_rga(raw,communes),on='codeEpci',how='left')
    t['rga_missing']=t.rga_mid_share.isna().astype(int)
    t[['rga_mid_share','rga_high_share']]=t[['rga_mid_share','rga_high_share']].fillna(0)
    t['log_population']=np.log1p(t.population.fillna(0))
    missing=int(t[meteo].isna().any(axis=1).sum())
    if missing:raise ValueError(f'{missing} lignes sans indicateur météo.')
    meta={'source':source,'last_mature_year':mature,'data_cut':str(events.published.max().date()),'years':[years[0],years[-1]],
          'communes':int(t.insee.nunique()),'rows':int(len(t)),'positive_rate':float(t.y.mean()),
          'events_metropole':int(events.insee.isin(communes.code).sum()),'events_excluded_not_metropole':int((~events.insee.isin(communes.code)).sum()),
          'communes_without_rga':int(t.drop_duplicates('insee').rga_missing.sum()),'max_cell_distance_km':float(communes.cell_distance_km.max())}
    return t,events,meta
