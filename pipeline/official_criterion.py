"""Critère officiel (circulaire IOME2322937C) appliqué au SWI uniforme : contrôle sur 2024 et lien avec les arrêtés.

1. contrôle : le rapport Météo-France 2024 annonce 17 mailles au critère 1 et 34 (34 ; la conclusion écrit 25, avec 47 mailles au total) au critère 2 ;
2. sensibilité et précision du critère contre la reconnaissance communale 1989-2022 ;
3. 2026 provisoire (mois publiés).

python -m pipeline.official_criterion
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from catnat.swi import load_cube
from catnat.data import load_communes,assign_cells
from catnat.official import annual_minimum,official_criterion,provisional_ranks,WINDOW
ROOT=Path(__file__).resolve().parents[1]

def main():
    years,ids,cube,grid=load_cube();full=np.isfinite(cube).all(axis=(1,2))
    amin=annual_minimum(cube);amin_full=np.where(full[:,None],amin,np.nan);res,ranks=official_criterion(amin_full,years)
    out={'window_years':WINDOW,'first_evaluated_year':min(res),'by_year':{}}
    for y in sorted(res):
        r=res[y];out['by_year'][y]={'cells_valid':int(np.isfinite(r['rank']).sum()),'c1':int(r['c1'].sum()),'c2':int(r['c2'].sum()),'c1_or_c2':int((r['c1']|r['c2']).sum())}
    ctrl=out['by_year'].get(2024);out['check_2024_vs_report']={'ours':ctrl,'report':{'c1':17,'c2':34,'total':47,'note':'la conclusion du rapport écrit 25 mailles au critère 2 ; 47 = 17 + 30 mailles du critère 2 seul'}}
    print('2024',ctrl,'(rapport : 17 / 34 ou 25 / 47)')
    # Lien avec les arrêtés : commune → maille la plus proche, reconnaissance de l'année
    tab=pd.read_parquet(ROOT/'data/processed/commune_year.parquet')[['insee','year','y','cell']]
    pos={int(c):i for i,c in enumerate(ids)};rows=[]
    for y,r in res.items():
        d=tab[tab.year==y]
        if d.empty:continue
        ci=d.cell.map(pos).to_numpy();met=(r['c1']|r['c2'])[ci];c1=r['c1'][ci];rk=r['rank'][ci]
        rows.append(pd.DataFrame({'insee':d.insee.values,'year':y,'y':d.y.values,'c1':c1,'c1_or_c2':met,'rank':rk}))
    a=pd.concat(rows,ignore_index=True)
    def perf(m,name):
        tp=int((m&(a.y==1)).sum());fp=int((m&(a.y==0)).sum());fn=int((~m&(a.y==1)).sum())
        return {'critère':name,'communes_critère':int(m.sum()),'sensibilité':tp/max(tp+fn,1),'précision':tp/max(tp+fp,1)}
    out['vs_decrees']=[perf(a.c1,'critère 1'),perf(a.c1_or_c2,'critère 1 ou 2')]
    from sklearn.metrics import roc_auc_score
    out['auc_rank_vs_decrees']=float(roc_auc_score(a.y,-a['rank'].fillna(a['rank'].max())))
    by=a.groupby('year').apply(lambda d:pd.Series({'recognised':int(d.y.sum()),'c1_or_c2_communes':int(d.c1_or_c2.sum()),'tp':int((d.c1_or_c2&(d.y==1)).sum())}))
    out['by_year_commune']=by.reset_index().to_dict('records');print(json.dumps(out['vs_decrees'],ensure_ascii=False,indent=1),'AUC rang',out['auc_rank_vs_decrees'])
    # 2026 provisoire
    ylast=int(years[-1]);prov=provisional_ranks(amin[-1],amin_full[years<ylast],ranks,ylast);c1=prov['c1'];c2=prov['c2'];r0=prov['rank']
    nm=int(np.isfinite(cube[-1]).any(axis=0).sum() and np.isfinite(cube[-1][0]).sum())
    out['provisional_last_year']={'year':ylast,'months_published':nm,'c1_cells':int(c1.sum()),'c2_cells':int(c2.sum()),'c1_or_c2_cells':int((c1|c2).sum()),'share_territory':float((c1|c2).mean()),'rank1_cells':int((r0==1).sum()),
        'note':'provisoire : indice minimum des mois publiés ; il ne peut que baisser ensuite'}
    print(out['provisional_last_year']);np.savez_compressed(ROOT/'data/processed/official_last.npz',cells=ids,rank=r0,c1=c1,c2=c2,year=ylast)
    (ROOT/'reports/official_criterion.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
    print('écrit')

if __name__=='__main__':main()
