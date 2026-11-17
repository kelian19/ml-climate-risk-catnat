"""Part de surface de chaque commune par classe d'aléa retrait-gonflement (BRGM, carte d'exposition, niveaux 1 à 3).

Entrée : data/raw/rga_brgm/alea.zip (AleaRG_2025_Fxx_L93, Shapefile Lambert 93, 121 399 polygones).
Sortie : data/raw/rga_commune.csv (insee, rga_c_low, rga_c_mid, rga_c_high) ; la surface hors carte d'exposition
(aléa a priori nul) n'est pas dans les trois classes. Calcul par département (intersection polygone à polygone) ;
les communes sont les contours Etalab simplifiés à 100 m, ce qui limite la précision des parts (quelques %).
"""
import numpy as np
import pandas as pd
import geopandas as gpd
import pyogrio
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'data/raw'
SHP='/vsizip/'+(RAW/'rga_brgm/alea.zip').as_posix()+'/AleaRG_2025_Fxx_L93.shp'

def main():
    com=gpd.read_file('/vsigzip/'+(RAW/'communes-100m.geojson.gz').as_posix());com=com[~com.code.str.startswith(('97','98'))][['code','departement','geometry']].to_crs(2154)
    com['geometry']=com.geometry.make_valid();com['area']=com.geometry.area
    rows=[]
    for dep,sub in com.groupby('departement'):
        rga=pyogrio.read_dataframe(SHP,where=f"insee_dep = '{dep}'")
        if rga.empty:continue
        rga['geometry']=rga.geometry.make_valid();rga=rga[['niveau','geometry']]
        inter=gpd.overlay(sub[['code','geometry']],rga,how='intersection',keep_geom_type=True)
        inter['a']=inter.geometry.area
        g=inter.groupby(['code','niveau']).a.sum().unstack(fill_value=0.).reindex(columns=[1.,2.,3.],fill_value=0.)
        g=g.join(sub.set_index('code').area.rename('area'));
        for k,name in [(1.,'rga_c_low'),(2.,'rga_c_mid'),(3.,'rga_c_high')]:g[name]=(g[k]/g.area).clip(0,1)
        rows.append(g[['rga_c_low','rga_c_mid','rga_c_high']].reset_index().rename(columns={'code':'insee'}));print(dep,len(sub),flush=True)
    out=pd.concat(rows,ignore_index=True)
    # Communes sans aucun polygone d'exposition : parts nulles (hors zone cartographiée), distinctes des communes absentes.
    missing=sorted(set(com.code)-set(out.insee));out=pd.concat([out,pd.DataFrame({'insee':missing,'rga_c_low':0.,'rga_c_mid':0.,'rga_c_high':0.})],ignore_index=True)
    out.to_csv(RAW/'rga_commune.csv',index=False);print(len(out),'communes ;',len(missing),'sans polygone d’exposition')
    print(out[['rga_c_low','rga_c_mid','rga_c_high']].describe().round(3))

if __name__=='__main__':main()
