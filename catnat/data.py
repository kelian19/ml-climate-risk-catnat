"""Chargement des sources publiques (voir pipeline/download.py) et jointure grille Safran / communes."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
DROUGHT_LABELS=('Sécheresse','Retrait-gonflement des argiles')
SIM_COLUMNS=['LAMBX','LAMBY','DATE','SWI','SSWI3','SSWI12']

def load_cells(raw=RAW):
    """Points de grille Safran-Isba (≈ 8 km) du shapefile Météo-France ; lecture du .dbf et des coordonnées en degrés."""
    import geopandas as gpd
    g=gpd.read_file(raw/'SHP_SIM_FRANCE.shp')
    return pd.DataFrame({'cell':g.num_maille.astype(int),'lambx':g.lambx.astype(int),'lamby':g.lamby.astype(int),'lon':g.lon_dg,'lat':g.lat_dg})

def load_communes(raw=RAW):
    """Communes de France métropolitaine, avec centre, population, surface (km²) et EPCI."""
    d=pd.DataFrame(json.loads((raw/'communes.json').read_text(encoding='utf-8')))
    d=d[~d.code.str.startswith(('97','98'))].copy()
    d['lon']=d.centre.map(lambda c:c['coordinates'][0]);d['lat']=d.centre.map(lambda c:c['coordinates'][1])
    d['surface_km2']=d.surface/100.
    return d.drop(columns=['centre','surface']).reset_index(drop=True)

def assign_cells(communes,cells):
    """Maille Safran la plus proche du centre de chaque commune (distance en km, Lambert-93)."""
    t=Transformer.from_crs(4326,2154,always_xy=True)
    cx,cy=t.transform(communes.lon.values,communes.lat.values);gx,gy=t.transform(cells.lon.values,cells.lat.values)
    dist,idx=cKDTree(np.c_[gx,gy]).query(np.c_[cx,cy])
    out=communes.copy();out['cell']=cells.cell.values[idx];out['cell_distance_km']=dist/1000.
    return out

def load_sim(years,raw=RAW):
    """SIM mensuelle Safran-Isba : SWI, SSWI3 et SSWI12 par maille et par mois."""
    frames=[]
    for y in years:
        f=pd.read_csv(raw/f'MENS_SIM2_{y}.csv.gz',sep=';',usecols=SIM_COLUMNS)
        frames.append(f)
    sim=pd.concat(frames,ignore_index=True)
    sim['year']=sim.DATE//100;sim['month']=sim.DATE%100
    return sim.drop(columns='DATE')

def load_events(raw=RAW):
    """Arrêtés de reconnaissance CatNat sécheresse par commune (une ligne par arrêté)."""
    c=pd.read_csv(raw/'catnat.csv',sep=';',header=None,dtype=str)
    c=c[c[12].isin(DROUGHT_LABELS)].copy()
    out=pd.DataFrame({'insee':c[1].str.zfill(5),'peril':c[12],'start':pd.to_datetime(c[13]),'end':pd.to_datetime(c[14]),'published':pd.to_datetime(c[15])})
    return out.reset_index(drop=True)

def load_rga(raw=RAW,communes=None):
    """Exposition RGA par EPCI : part de surface d'aléa moyen et fort. La part est rapportée à la surface
    de l'EPCI reconstituée par la somme de ses communes ; les EPCI absents ou non renseignés restent manquants."""
    r=pd.read_csv(raw/'rga_epci.csv',sep=None,engine='python',dtype=str)
    r['v']=pd.to_numeric(r.VALEUR_EXPOSITION.str.replace(',','.'),errors='coerce')
    w=r.pivot_table(index='EPCI_CODE',columns='INDICATEUR_EXPOSITION',values='v',aggfunc='first')
    area=communes.groupby('codeEpci').surface_km2.sum().rename('epci_area_km2')
    w=w.join(area,how='left')
    w['rga_mid_share']=(w.Surface_exposee_RGA2_km2/w.epci_area_km2).clip(0,1)
    w['rga_high_share']=(w.Surface_exposee_RGA3_km2/w.epci_area_km2).clip(0,1)
    return w[['rga_mid_share','rga_high_share']].reset_index().rename(columns={'EPCI_CODE':'codeEpci'})
