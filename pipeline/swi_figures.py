"""Figures du SWI uniforme à partir de reports/swi_study.json et des prévisions enregistrées."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];FIG=ROOT/'reports/figures'

def main():
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    r=json.loads((ROOT/'reports/swi_study.json').read_text(encoding='utf-8'))
    pred=pd.read_parquet(ROOT/'data/processed/swi_forecast.parquet')
    ann=pred.groupby('year')[['target','p_persistance','p_climatologie','p_ridge','p_gbm','p_rf']].mean()
    fig,ax=plt.subplots(figsize=(8.5,4))
    ax.plot(ann.index,ann.target,'k-o',ms=3,label='Observé')
    for c,l,s in [('p_climatologie','Climatologie','--'),('p_persistance','Persistance','-.'),('p_ridge','Ridge',' -'),('p_rf','Forêt aléatoire',':')]:
        ax.plot(ann.index,ann[c],s.strip() or '-',label=l)
    ax.set_ylabel('SWI uniforme JJA, moyenne nationale');ax.set_title('Prévision fin mai du SWI uniforme d’été (hors échantillon)');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(FIG/'swi_prevision.png',dpi=130);plt.close(fig)
    g=r['geostat'];v=g['variogram'];fig,ax=plt.subplots(figsize=(6,4))
    ax.scatter(v['lag_km'],v['gamma'],s=np.clip(np.array(v['pairs'])/2000,6,60),color='k',label='Empirique')
    h=np.linspace(0,max(v['lag_km']),200)
    from catnat.geostat import MODELS
    for m,p in g['fits'].items():ax.plot(h,MODELS[m](h*1000,p['nugget'],p['psill'],p['range']),label=f"{m} (portée {p['range']/1000:.0f} km)")
    ax.set_xlabel('Distance (km)');ax.set_ylabel('Semi-variogramme');ax.set_title(f"SWI uniforme d’été {g['year']}");ax.legend(fontsize=8);fig.tight_layout();fig.savefig(FIG/'swi_variogramme.png',dpi=130);plt.close(fig)
    c=r['criterion']['25']['by_year'];d=pd.DataFrame(c)
    fig,ax=plt.subplots(figsize=(8.5,3.8));ax.bar(d.year-0.2,d.criterion,0.4,label='Critère SWI reconstitué (T = 25 ans)',color='#c9d6c2');ax.bar(d.year+0.2,d.decrees,0.4,label='Communes reconnues',color='#b24a3a')
    ax.set_ylabel('Communes');ax.legend(fontsize=8);ax.set_title('Critère météorologique reconstitué et reconnaissances effectives');fig.tight_layout();fig.savefig(FIG/'swi_critere.png',dpi=130);plt.close(fig)

if __name__=='__main__':main()
