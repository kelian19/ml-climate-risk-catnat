"""SWI uniforme Météo-France (configuration de sol argileux et de couvert gazonné identique partout,
utilisée pour le critère météorologique du dispositif CatNat sécheresse).

Le fichier de suivi (1958-08 → mois courant) et le fichier de référence CatNat (1960-2025) sont
identiques sur leur recouvrement (vérifié dans les tests) ; on utilise le suivi, plus long, restreint
aux 8 981 mailles de référence. Représentation : cube année × maille × mois (NaN si non publié).
"""
import glob
import numpy as np
import pandas as pd
from .data import RAW

FIRST_YEAR=1959

def load_grid(raw=RAW):
    g=pd.read_csv(raw/'swi_mailles.csv',sep=';',comment='#',header=None,names=['cell','lambx','lamby','x93','y93','lat','lon'])
    return g.sort_values('cell').reset_index(drop=True)

def load_long(raw=RAW,source='suivi'):
    pattern='swi_uniforme.*.csv.gz' if source=='suivi' else 'swi.*.csv.gz'
    frames=[]
    for f in sorted(glob.glob(str(raw/pattern))):
        d=pd.read_csv(f,sep=';');d.columns=[c.strip('"') for c in d.columns];frames.append(d[['NUMERO','DATE','SWI_UNIF_MENS']])
    d=pd.concat(frames,ignore_index=True).rename(columns={'NUMERO':'cell','SWI_UNIF_MENS':'swi'})
    d['year']=d.DATE//100;d['month']=d.DATE%100
    return d.drop(columns='DATE')

def to_cube(long,cells,first_year=FIRST_YEAR,last_year=None):
    d=long[long.cell.isin(cells)&(long.year>=first_year)]
    last_year=last_year or int(d.year.max())
    d=d[d.year<=last_year]
    years=np.arange(first_year,last_year+1);ids=np.sort(np.asarray(cells))
    cube=np.full((len(years),len(ids),12),np.nan)
    cube[d.year.values-first_year,np.searchsorted(ids,d.cell.values),d.month.values-1]=d.swi.values
    return years,ids,cube

def load_cube(raw=RAW,last_year=None):
    grid=load_grid(raw);years,ids,cube=to_cube(load_long(raw),grid.cell.values,last_year=last_year)
    return years,ids,cube,grid

def rolling_quarter_means(cube):
    """Moyennes glissantes sur 3 mois consécutifs se terminant au mois m (m = 1…12), y compris à cheval
    sur l'année précédente (novembre-décembre-janvier…). Forme : année × maille × 12."""
    y,c,_=cube.shape
    series=cube.transpose(1,0,2).reshape(c,y*12)  # maille × temps mensuel
    q=np.full_like(series,np.nan)
    q[:,2:]=(series[:,2:]+series[:,1:-1]+series[:,:-2])/3
    return q.reshape(c,y,12).transpose(1,0,2)
