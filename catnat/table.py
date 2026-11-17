"""Assemblage de la table commune × année utilisée par les modèles."""
import numpy as np
from .data import RAW,load_cells,load_communes,assign_cells,load_sim,load_events,load_rga
from .features import build_features
from .labels import last_mature_year,build_labels,history_counts

FIRST_SIM_YEAR=2000

def build_table(raw=RAW,min_years=5):
    cells=load_cells(raw);communes=assign_cells(load_communes(raw),cells)
    events=load_events(raw);mature=last_mature_year(events)
    feats=build_features(load_sim(range(FIRST_SIM_YEAR,mature+1),raw),cells,min_years)
    years=sorted(int(y) for y in feats.year.unique() if y<=mature)
    t=build_labels(events,communes,years)
    t=t.merge(communes[['code','nom','codeDepartement','codeEpci','population','cell','cell_distance_km']],left_on='insee',right_on='code').drop(columns='code')
    t=t.merge(feats,on=['cell','year'],how='left')
    t=t.merge(history_counts(events,communes,years),on=['insee','year'],how='left')
    t['hist_count']=t.hist_count.fillna(0)
    t=t.merge(load_rga(raw,communes),on='codeEpci',how='left')
    t['rga_missing']=t.rga_mid_share.isna().astype(int)
    t[['rga_mid_share','rga_high_share']]=t[['rga_mid_share','rga_high_share']].fillna(0)
    t['log_population']=np.log1p(t.population.fillna(0))
    missing=int(t[['swi_jja_z','swi_son_z','swi_min_z','sswi3_sep','sswi12_dec','swi_jja_z_prev']].isna().any(axis=1).sum())
    if missing:raise ValueError(f'{missing} lignes sans indicateur météo.')
    meta={'last_mature_year':mature,'data_cut':str(events.published.max().date()),'years':[years[0],years[-1]],
          'communes':int(t.insee.nunique()),'rows':int(len(t)),'positive_rate':float(t.y.mean()),
          'events_metropole':int(events.insee.isin(communes.code).sum()),'events_excluded_not_metropole':int((~events.insee.isin(communes.code)).sum()),
          'communes_without_rga':int(t.drop_duplicates('insee').rga_missing.sum()),'max_cell_distance_km':float(communes.cell_distance_km.max())}
    return t,events,meta
