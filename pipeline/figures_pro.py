"""Figures détaillées : cartes communales, séries de cartes du SWI, calendrier, krigeage, éventail de prédiction, bivarié.

python -m pipeline.figures_pro            # toutes
python -m pipeline.figures_pro france swi calendar     # une sélection
"""
import json,sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize,TwoSlopeNorm,PowerNorm,ListedColormap
from matplotlib.gridspec import GridSpec
from catnat import viz
from catnat.viz import *
from catnat.swi import load_cube
from catnat.data import load_communes,assign_cells
from catnat.uncertainty import loo_year_coverage
ROOT=Path(__file__).resolve().parents[1];RAW=(ROOT/'data/raw').as_posix();OUT=ROOT/'reports/figures'
SRC='Sources : Météo-France (SWI uniforme), GASPAR/data.gouv.fr (arrêtés CatNat), BRGM/SDES (argiles), Etalab (contours). Modèle : régression logistique validée en temps réel.'

def ctx():
    setup();OUT.mkdir(parents=True,exist_ok=True)
    com,dep,reg=base_layers(RAW);pred=pd.read_parquet(ROOT/'data/processed/predictions.parquet');tab=pd.read_parquet(ROOT/'data/processed/commune_year.parquet')
    ete=pd.read_csv(ROOT/'reports/ete_2026_communes.csv',dtype={'insee':str});e=json.loads((ROOT/'reports/ete_2026.json').read_text(encoding='utf-8'))
    return dict(com=com,dep=dep,reg=reg,pred=pred,tab=tab,ete=ete,e=e)

DPI=150   # 3 000 à 3 900 pixels de large : assez pour zoomer, sans alourdir le dépôt (200 ppp donnait 3 à 4,5 Mo par figure)

def save(fig,name):
    """PNG en RVB sans canal alpha (fond opaque), compression maximale ; aucune réduction de palette, les couleurs portent la donnée."""
    import io
    from PIL import Image
    buf=io.BytesIO();fig.savefig(buf,format='png',dpi=DPI);plt.close(fig);buf.seek(0)
    Image.open(buf).convert('RGB').save(OUT/f'pro_{name}.png',optimize=True);print('écrit',name,flush=True)

def fig_france(c):
    com=c['com'];p=c['pred'];g=p.groupby('insee').agg(obs=('y','mean'),mod=('p_glm_complet','mean')).reset_index();d=com.merge(g,left_on='code',right_on='insee',how='left');d['diff']=d.obs-d['mod']
    fig=plt.figure(figsize=(21,9.4));gs=GridSpec(1,3,figure=fig,left=0.01,right=0.99,top=0.88,bottom=0.1,wspace=0.02);y0,y1=int(p.year.min()),int(p.year.max())
    specs=[('obs','Fréquence observée de reconnaissance',DRY,PowerNorm(0.55,0,0.45),lambda v,_:f'{100*v:.0f} %','Part des années reconnues'),
           ('mod','Fréquence prédite (hors échantillon)',DRY,PowerNorm(0.55,0,0.45),lambda v,_:f'{100*v:.0f} %','Part des années attendues'),
           ('diff','Écart observé − prédit',WET_DRY.reversed(),TwoSlopeNorm(0,-0.25,0.25),lambda v,_:f'{100*v:+.0f} pts','Sous-estimé (rouge) / surestimé (bleu)')]
    for k,(col,title,cm,norm,fmt,lab) in enumerate(specs):
        ax=fig.add_subplot(gs[k]);d.plot(column=col,ax=ax,cmap=cm,norm=norm,linewidth=0,missing_kwds={'color':'#e5e5e5'},rasterized=True)
        finish_map(ax,c['dep'],c['reg']);ax.set_title(title,pad=4)
        if k==0:label_regions(ax,c['reg'],6.5);scale_bar(ax,200);north_arrow(ax)
        hbar_colorbar(fig,ax,cm,norm,lab,fmt=fmt)
    title_block(fig,'Sécheresse CatNat : où et à quelle fréquence les communes sont reconnues',f'{y0}–{y1}, 34 746 communes. Une commune est reconnue si un arrêté sécheresse porte sur un événement de l’année ; les prévisions sont hors échantillon.',SRC)
    save(fig,'france_triptyque')

def fig_swi_years(c):
    com=c['com'];years,ids,cube,grid=load_cube();summer=cube[:,:,5:8].mean(axis=2);mu=np.nanmean(summer[:-1],axis=0);sd=np.nanstd(summer[:-1],axis=0,ddof=1);z=(summer-mu)/sd
    cells=assign_cells(load_communes(),grid[['cell','lon','lat']])[['code','cell']];idx={v:i for i,v in enumerate(ids)};cells['i']=cells.cell.map(idx)
    sel=[1976,1989,2003,2011,2019,2022,2025,2026];fig=plt.figure(figsize=(20,10.8));gs=GridSpec(2,4,figure=fig,left=0.01,right=0.99,top=0.88,bottom=0.12,wspace=0.0,hspace=0.1)
    norm=TwoSlopeNorm(0,-3,2.5);cm=WET_DRY.reversed();obs=c['tab'].groupby('year').y.sum()
    for k,y in enumerate(sel):
        ax=fig.add_subplot(gs[k//4,k%4]);t=int(np.where(years==y)[0][0]);d=com.merge(cells[['code','i']],on='code');d['z']=z[t,d.i.astype(int).values]
        d.plot(column='z',ax=ax,cmap=cm,norm=norm,linewidth=0,rasterized=True);finish_map(ax,c['dep'],c['reg'],dep_lw=0.1,reg_lw=0.5)
        sub=f"{int(obs[y]):,} communes reconnues".replace(',',' ') if y in obs.index else ('estimation : voir carte 2026' if y==2026 else 'arrêtés non mûrs')
        ax.set_title(f"{y}",loc='left',fontsize=15,color=ACCENT);ax.text(0.01,0.02,f"{sub}\nanomalie nationale {np.nanmean(z[t]):+.2f} σ",transform=ax.transAxes,fontsize=7.5,color=INK,va='bottom')
    cax=fig.add_axes([0.35,0.062,0.3,0.013]);cb=fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap=cm),cax=cax,orientation='horizontal');cb.set_label('Anomalie du SWI uniforme d’été (écarts-types) : sec (brun) ← → humide (bleu)',fontsize=8);cb.ax.tick_params(labelsize=7)
    title_block(fig,'Les étés secs vus par le SWI uniforme','Anomalie du SWI uniforme juin-août par rapport à la moyenne 1959–2025 de chaque maille, projetée sur les communes. 2026 : données jusqu’en septembre.',SRC)
    save(fig,'swi_etes_secs')

def fig_calendar(c):
    t=c['tab'];d=c['dep'].copy();d['cy']=d.geometry.centroid.y;order=d.sort_values('cy',ascending=False).departement.tolist()
    m=t.groupby(['codeDepartement','year']).y.mean().unstack();m=m.reindex(order);years=m.columns.values
    fig=plt.figure(figsize=(15.5,13));gs=GridSpec(2,2,figure=fig,width_ratios=[1,0.12],height_ratios=[0.16,1],left=0.07,right=0.97,top=0.9,bottom=0.06,hspace=0.03,wspace=0.02)
    a0=fig.add_subplot(gs[0,0]);a1=fig.add_subplot(gs[1,0]);a2=fig.add_subplot(gs[1,1])
    obs=t.groupby('year').y.sum();a0.bar(obs.index,obs.values,color='#c9d6c2',width=0.85,label='Communes reconnues')
    pr=c['pred'].groupby('year').p_glm_complet.sum();a0.plot(pr.index,pr.values,'-o',ms=3,color=ACCENT,lw=1.4,label='Attendu (modèle)');a0.set_xlim(years[0]-.5,years[-1]+.5);a0.set_xticks([]);a0.legend(fontsize=8,frameon=False,loc='upper left')
    a0.set_ylabel('Communes',fontsize=8);[a0.spines[s].set_visible(False) for s in ('top','right')]
    im=a1.imshow(m.values,aspect='auto',cmap=DRY,norm=PowerNorm(0.5,0,0.6),interpolation='nearest',extent=[years[0]-.5,years[-1]+.5,len(order)-.5,-.5])
    a1.set_yticks(range(0,len(order),1));a1.set_yticklabels(order,fontsize=5.6);a1.set_xticks(years[::2]);a1.tick_params(axis='x',labelsize=8,rotation=90);a1.set_xlabel('Année de l’événement')
    for y in (2003,2011,2018,2022):a1.axvline(y,color=INK,lw=0.4,alpha=0.35)
    tot=m.mean(axis=1);a2.barh(range(len(order)),tot.values,color=ACCENT,height=0.8);a2.set_ylim(len(order)-.5,-.5);a2.set_yticks([]);a2.set_xlabel('Moyenne',fontsize=8);[a2.spines[s].set_visible(False) for s in ('top','right')]
    cax=fig.add_axes([0.07,0.022,0.35,0.012]);cb=fig.colorbar(im,cax=cax,orientation='horizontal');cb.set_label('Part des communes du département reconnues',fontsize=8);cb.ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v,_:f'{100*v:.0f} %'));cb.ax.tick_params(labelsize=7)
    title_block(fig,'Calendrier des reconnaissances : département × année','Départements ordonnés du nord au sud ; chaque case est la part de ses communes reconnues pour un événement de l’année.',SRC)
    save(fig,'calendrier_departements')

METHOD_NAMES={'empirique_tout':'quantiles empiriques, tout l’historique','empirique_recent':'quantiles empiriques, 10 dernières années',
              'lognormal_tout':'loi log-normale, tout l’historique','lognormal_recent':'loi log-normale, 10 dernières années'}

def fig_fan(c):
    """Intervalle unique retenu : bornes calculées en temps réel chaque année (seules les années passées connues), puis 2026."""
    t=c['tab'];e=c['e'];h=e['headline_interval'];by=pd.DataFrame(e['backtest_by_year'])
    rt=pd.read_csv(ROOT/'reports/interval_realtime.csv');rt=rt[rt.method==h['method']]
    fig=plt.figure(figsize=(15,9.5));gs=GridSpec(2,1,figure=fig,height_ratios=[1,0.38],left=0.07,right=0.97,top=0.88,bottom=0.08,hspace=0.12)
    a=fig.add_subplot(gs[0]);lvl=int(round(100*h['level']))
    a.fill_between(rt.year,rt.low,rt.high,color='#a9c9a3',step=None,label=f"Intervalle à {lvl} % calculé en temps réel (couverture constatée {100*h['realtime_coverage']:.0f} % sur {h['realtime_years']} ans)")
    a.plot(by.year,by.expected,'-',color=ACCENT,lw=1.8,label='Attendu par le modèle');a.scatter(by.year,by.observed,s=36,color=WARN,zorder=5,label='Observé')
    for r in rt.itertuples():
        if not r.covered:a.annotate(str(r.year),(r.year,r.observed),xytext=(0,8),textcoords='offset points',ha='center',fontsize=7,color=WARN)
    x=2026.7;est=e['expected_recognised_communes']
    a.errorbar([x],[est],yerr=[[est-h['low']],[h['high']-est]],fmt='none',ecolor=ACCENT,elinewidth=8,alpha=.9,capsize=0);a.scatter([x],[est],s=60,color='white',edgecolor=INK,zorder=6)
    a.annotate(f"2026 (estimation)\n{est:,.0f} communes attendues\nintervalle à {lvl} % : {h['low']:,.0f} – {h['high']:,.0f}".replace(',',' '),(x,est),xytext=(-170,46),textcoords='offset points',fontsize=8.5,arrowprops=dict(arrowstyle='-',color=MUTED))
    a.set_yscale('symlog',linthresh=100);a.set_ylabel('Communes reconnues (échelle symlog)');a.set_xlim(1994,2028.2);a.legend(fontsize=8,frameon=False,loc='upper left');a.tick_params(labelbottom=False)
    for s_ in ('top','right'):a.spines[s_].set_visible(False)
    b=fig.add_subplot(gs[1],sharex=a);sev=t.groupby('year').rp_max_log.mean();sev=sev[sev.index>=1995];b.fill_between(sev.index,0,sev.values,color='#e8a43c',alpha=.6);b.plot(sev.index,sev.values,color='#a3361b',lw=1.4)
    s26=e['severity']['rp_max_log_mean'];b.scatter([2026],[s26],color=WARN,s=50,zorder=5);b.annotate(f'2026 : {s26:.2f}',(2026,s26),xytext=(-60,-4),textcoords='offset points',fontsize=8,color=WARN)
    b.set_ylabel('ln(période de retour)\nmoyenne communale',fontsize=8);b.set_xlabel('Année de l’événement');[b.spines[s].set_visible(False) for s in ('top','right')]
    title_block(fig,'Un intervalle unique pour 2026, éprouvé sur le passé',f"Méthode retenue par score d’intervalle en temps réel : {METHOD_NAMES[h['method']]} du rapport observé/attendu ; chaque bande est calculée avec les seules années déjà connues à la date.",SRC)
    save(fig,'eventail_prediction')

def fig_nowcast(c):
    com=c['com'];ete=c['ete'];e=c['e'];d=com.merge(ete,left_on='code',right_on='insee',how='left');d['width']=d.p_hi-d.p_lo
    fig=plt.figure(figsize=(21,9.2));gs=GridSpec(1,3,figure=fig,left=0.01,right=0.985,top=0.87,bottom=0.1,wspace=0.03,width_ratios=[1,1,0.8])
    a=fig.add_subplot(gs[0]);d.plot(column='p',ax=a,cmap=DRY,vmin=0,vmax=1,linewidth=0,rasterized=True);finish_map(a,c['dep'],c['reg']);a.set_title('Probabilité estimée de reconnaissance en 2026');label_regions(a,c['reg'],6.5);scale_bar(a);north_arrow(a)
    hbar_colorbar(fig,a,DRY,Normalize(0,1),'Probabilité',fmt=lambda v,_:f'{100*v:.0f} %')
    b=fig.add_subplot(gs[1]);cm2=LinearSegmentedColormap.from_list('w',['#f4f7ef','#a9c9d8','#4a7fa8','#1c3f6e']);d.plot(column='width',ax=b,cmap=cm2,vmin=0,vmax=0.5,linewidth=0,rasterized=True);finish_map(b,c['dep'],c['reg']);b.set_title('Largeur de l’intervalle à 90 % (incertitude statistique)')
    hbar_colorbar(fig,b,cm2,Normalize(0,0.5),'Borne haute − borne basse (points de probabilité)',fmt=lambda v,_:f'{100*v:.0f} pts')
    dd=d.merge(c['dep'][['departement']],on='departement',how='left');g=dd.groupby('departement').agg(exp=('p','sum'),lo=('p_lo','sum'),hi=('p_hi','sum')).sort_values('exp',ascending=False).head(22).iloc[::-1]
    r=fig.add_subplot(gs[2]);r.barh(range(len(g)),g.exp,color=ACCENT,height=0.7);r.errorbar(g.exp,range(len(g)),xerr=[g.exp-g.lo,g.hi-g.exp],fmt='none',ecolor=WARN,elinewidth=1.4,capsize=2.5)
    r.set_yticks(range(len(g)));r.set_yticklabels(g.index,fontsize=7.5);r.set_xlabel('Communes attendues (barres : sommes des bornes communales 5–95 %, conservatrices)',fontsize=8);r.set_title('Départements les plus touchés');[r.spines[s].set_visible(False) for s in ('top','right')]
    est=e['expected_recognised_communes'];title_block(fig,'Sécheresse 2026 : estimation par commune avec incertitude',f"SWI uniforme jusqu’en septembre 2026 ; {est:,.0f} communes attendues, intervalle retenu à {100*e['headline_interval']['level']:.0f} % : {e['headline_interval']['low']:,.0f}–{e['headline_interval']['high']:,.0f} ; arrêtés non publiés.".replace(',',' '),SRC)
    save(fig,'nowcast_2026')

def fig_krige(c):
    from catnat.geostat import empirical_variogram,fit_variogram,ordinary_kriging,MODELS
    from shapely.geometry import Point
    import shapely
    years,ids,cube,grid=load_cube();t=int(np.where(years==2022)[0][0]);z=cube[t,:,5:8].mean(axis=1);xy=grid[['x93','y93']].to_numpy(float)
    lag,gam,cnt=empirical_variogram(xy,z,400000.,25);fits={m:fit_variogram(lag,gam,cnt,m) for m in MODELS};best=min(fits,key=lambda m:fits[m]['wrmse']);par=fits[best]
    rng=np.random.default_rng(3);keep=np.sort(rng.choice(len(z),450,replace=False));test=np.setdiff1d(np.arange(len(z)),keep);xo,zo=xy[keep],z[keep]
    france=c['com'].geometry.union_all();shapely.prepare(france);step=6000.;xs=np.arange(xy[:,0].min(),xy[:,0].max(),step);ys=np.arange(xy[:,1].min(),xy[:,1].max(),step);XX,YY=np.meshgrid(xs,ys)
    pts=np.c_[XX.ravel(),YY.ravel()];inside=shapely.contains_xy(france,pts[:,0],pts[:,1]);P,V=ordinary_kriging(xo,zo,pts[inside],par,n_neighbors=20)
    Z=np.full(len(pts),np.nan);S=np.full(len(pts),np.nan);Z[inside]=P;S[inside]=np.sqrt(V);Z=Z.reshape(XX.shape);S=S.reshape(XX.shape)
    Pt,Vt=ordinary_kriging(xo,zo,xy[test],par,n_neighbors=20);err=z[test]-Pt;sdt=np.sqrt(np.maximum(Vt,1e-12));cover=float(np.mean(np.abs(err)<=1.96*sdt));rmse=float(np.sqrt(np.mean(err**2)))
    fig=plt.figure(figsize=(26,8.6));gs=GridSpec(1,4,figure=fig,left=0.01,right=0.985,top=0.87,bottom=0.1,wspace=0.03,width_ratios=[1,1,1,0.85]);ext=[xs[0],xs[-1],ys[0],ys[-1]]
    a=fig.add_subplot(gs[0]);im=a.imshow(Z,origin='lower',extent=ext,cmap=WET_DRY.reversed(),vmin=0.0,vmax=0.9,interpolation='bilinear');a.scatter(xo[:,0],xo[:,1],s=5,color=INK,alpha=.55,lw=0);c['reg'].boundary.plot(ax=a,color=INK,lw=0.6,alpha=.7);a.set_axis_off();a.set_title('Surface krigée à partir de 450 mailles (points)');a.set_aspect('equal')
    cb=fig.colorbar(im,cax=a.inset_axes([0.2,-0.05,0.6,0.018]),orientation='horizontal');cb.set_label('SWI uniforme JJA 2022 : sec (brun) ← → humide (bleu)',fontsize=8);cb.ax.tick_params(labelsize=7)
    b=fig.add_subplot(gs[1]);im2=b.imshow(S,origin='lower',extent=ext,cmap='YlOrRd',vmin=0,vmax=np.nanquantile(S,0.995),interpolation='bilinear');b.scatter(xo[:,0],xo[:,1],s=5,color=INK,alpha=.55,lw=0);c['reg'].boundary.plot(ax=b,color=INK,lw=0.6,alpha=.7);b.set_axis_off();b.set_aspect('equal');b.set_title('Écart-type de krigeage : l’incertitude croît loin des mailles')
    cb=fig.colorbar(im2,cax=b.inset_axes([0.2,-0.05,0.6,0.018]),orientation='horizontal');cb.set_label('Écart-type (unités de SWI)',fontsize=8);cb.ax.tick_params(labelsize=7)
    e_=fig.add_subplot(gs[2]);sc=e_.scatter(xy[test,0],xy[test,1],c=np.abs(err),s=9,marker='s',lw=0,cmap='YlOrRd',vmin=0,vmax=np.quantile(np.abs(err),0.99),rasterized=True);c['reg'].boundary.plot(ax=e_,color=INK,lw=0.6,alpha=.7);e_.set_axis_off();e_.set_aspect('equal')
    e_.set_title(f'Erreur absolue sur les 8 531 mailles non utilisées');cb=fig.colorbar(sc,cax=e_.inset_axes([0.2,-0.05,0.6,0.018]),orientation='horizontal');cb.set_label(f'|vrai − krigé| ; RMSE {rmse:.3f} ; couverture à 95 % : {100*cover:.0f} %',fontsize=8);cb.ax.tick_params(labelsize=7)
    v=fig.add_subplot(gs[3]);v.scatter(lag/1000,gam,s=np.clip(cnt/3000,10,90),color=INK,alpha=.75,label='Empirique (taille = nb. de paires)');h=np.linspace(0,lag.max(),300)
    for m,p in fits.items():v.plot(h/1000,MODELS[m](h,p['nugget'],p['psill'],p['range']),lw=2.2 if m==best else 1,alpha=1 if m==best else .6,label=f"{m} (portée {p['range']/1000:.0f} km{' — retenu' if m==best else ''})")
    v.set_xlabel('Distance (km)');v.set_ylabel('Semi-variogramme');v.set_title('Variogramme (8 981 mailles)');v.legend(fontsize=7.5,frameon=False,loc='lower right');[v.spines[s_].set_visible(False) for s_ in ('top','right')]
    title_block(fig,'Krigeage du SWI uniforme : surface et incertitude','Krigeage ordinaire (20 voisins) d’un réseau clairsemé de 450 mailles, validé sur les 8 531 autres, été 2022 ; variogramme estimé sur toutes les mailles.',SRC)
    save(fig,'krigeage_swi')

def fig_bivariate(c):
    import pathlib
    rp=ROOT/'data/raw/rga_commune.csv'
    if not rp.exists():print('rga_commune.csv absent : carte bivariée ignorée');return
    com=c['com'];from catnat.features import build_features_uniform
    years,ids,cube,grid=load_cube();feats=build_features_uniform(cube,years,ids,10,last_month=9);f=feats[feats.year==2026][['cell','rp_max_log']]
    cells=assign_cells(load_communes(),grid[['cell','lon','lat']])[['code','cell']];rga=pd.read_csv(rp,dtype={'insee':str}).rename(columns={'insee':'code'})
    d=com.merge(cells,on='code',how='left').merge(f,on='cell',how='left').merge(rga,on='code',how='left');d['clay']=(d.rga_c_mid.fillna(0)+d.rga_c_high.fillna(0))
    qx=np.nanquantile(d.rp_max_log,[1/3,2/3]);qy=np.nanquantile(d.clay,[1/3,2/3]);col,ix,iy=bivariate_colors(d.rp_max_log.fillna(0).values,d.clay.values,qx,qy,1);d['col']=col
    fig=plt.figure(figsize=(20,9.4));gs=GridSpec(1,3,figure=fig,left=0.01,right=0.985,top=0.87,bottom=0.13,wspace=0.03,width_ratios=[1,1,0.5])
    a=fig.add_subplot(gs[0]);cm=SEQ_GREEN;d.plot(column='clay',ax=a,cmap=cm,vmin=0,vmax=1,linewidth=0,rasterized=True);finish_map(a,c['dep'],c['reg']);a.set_title('Aléa retrait-gonflement : part de la commune en aléa moyen ou fort')
    hbar_colorbar(fig,a,cm,Normalize(0,1),'Part de la surface (BRGM, carte d’exposition 2025)',fmt=lambda v,_:f'{100*v:.0f} %')
    b=fig.add_subplot(gs[1]);d.plot(ax=b,color=d.col.tolist(),linewidth=0,rasterized=True);finish_map(b,c['dep'],c['reg']);b.set_title('Argile × sévérité du SWI uniforme 2026 (terciles)');label_regions(b,c['reg'],6.5);scale_bar(b)
    l=fig.add_subplot(gs[2]);l.set_position([0.76,0.45,0.2,0.3]);bivariate_legend(l,'Sévérité 2026','Aléa argile',1)
    fig.text(0.76,0.38,'Rouge-brun : argile forte et sécheresse sévère\n= communes les plus exposées en 2026.\nJaune : sécheresse sévère mais argile peu présente ;\nrose : argile forte mais sécheresse modérée.',fontsize=8,color=INK,va='top')
    title_block(fig,'Là où l’argile rencontre la sécheresse','Carte bivariée par terciles : exposition aux argiles gonflantes (BRGM) et sévérité du SWI uniforme 2026 (période de retour maximale).',SRC)
    save(fig,'bivarie_argile_secheresse')

def fig_region(c,code='24'):
    com=c['com'];ete=c['ete'];lc=load_communes();r=com[com.region==code].merge(ete,left_on='code',right_on='insee',how='left').merge(lc[['code','population']],on='code',how='left')
    rd=c['dep'][c['dep'].region==code];fig=plt.figure(figsize=(18,8.6));gs=GridSpec(1,2,figure=fig,left=0.01,right=0.99,top=0.86,bottom=0.08,wspace=0.02)
    for k,(col,title,cm,norm) in enumerate([('p','Probabilité estimée 2026',DRY,Normalize(0,1)),('p_hi','Borne haute de l’intervalle à 90 %',DRY,Normalize(0,1))]):
        ax=fig.add_subplot(gs[k]);r.plot(column=col,ax=ax,cmap=cm,norm=norm,linewidth=0.05,edgecolor='white',rasterized=True);rd.boundary.plot(ax=ax,color=INK,lw=1.1);ax.set_axis_off();ax.set_aspect('equal');ax.set_title(title)
        if k==0:
            for rr in r.sort_values('population',ascending=False).head(12).itertuples():
                pt=rr.geometry.representative_point();ax.text(pt.x,pt.y,f"{rr.nom_x if hasattr(rr,'nom_x') else rr.nom}\n{100*rr.p:.0f} %",fontsize=6.5,ha='center',va='center',color=INK,weight='bold',path_effects=[pe.withStroke(linewidth=2,foreground='white')])
            scale_bar(ax,50);north_arrow(ax)
        hbar_colorbar(fig,ax,cm,norm,'Probabilité',fmt=lambda v,_:f'{100*v:.0f} %')
    title_block(fig,f"{REG_NAMES[code]} : zoom communal 2026",'Probabilité estimée de reconnaissance et borne haute ; les 12 communes les plus peuplées sont étiquetées. Estimation : arrêtés non publiés.',SRC)
    save(fig,f'region_{code}_2026')

def fig_interp(c):
    z=np.load(ROOT/'data/processed/swi_commune.npz',allow_pickle=True);years,ids,cube,grid=load_cube();t=int(np.where(years==2026)[0][0]);r=json.loads((ROOT/'reports/spatial_interp.json').read_text(encoding='utf-8'))
    com=c['com'].merge(pd.DataFrame({'code':z['codes'],'krig':z['cube'][t,:,5:8].mean(axis=1),'var':z['krig_var'],'nearest_cell':z['nearest_cell']}),on='code',how='left')
    idx={v:i for i,v in enumerate(ids)};summer=cube[t,:,5:8].mean(axis=1);ci=com.nearest_cell.map(idx);com['nn']=np.where(ci.notna(),summer[ci.fillna(0).astype(int).values],np.nan);com['diff']=com.krig-com.nn;fv=np.nanvar(summer,ddof=1);com['sd']=np.sqrt(com['var']*fv)
    fig=plt.figure(figsize=(25,8.8));gs=GridSpec(1,4,figure=fig,left=0.01,right=0.985,top=0.87,bottom=0.1,wspace=0.04,width_ratios=[1,1,1,0.72])
    a=fig.add_subplot(gs[0]);cm=WET_DRY.reversed();com.plot(column='krig',ax=a,cmap=cm,vmin=0,vmax=0.6,linewidth=0,rasterized=True);finish_map(a,c['dep'],c['reg'],dep_lw=0.1);a.set_title('SWI uniforme d’été 2026 krigé au centre des communes');hbar_colorbar(fig,a,cm,Normalize(0,0.6),'SWI uniforme JJA : sec ← → humide')
    b=fig.add_subplot(gs[1]);cm2=LinearSegmentedColormap.from_list('sd',['#f4f7ef','#cfe3c4','#7fb77e','#3d8a63','#175b4a']);com.plot(column='sd',ax=b,cmap=cm2,linewidth=0,rasterized=True);finish_map(b,c['dep'],c['reg'],dep_lw=0.1);b.set_title('Écart-type d’estimation du krigeage (unités de SWI)')
    hbar_colorbar(fig,b,cm2,Normalize(com.sd.min(),com.sd.max()),'Écart-type',fmt=lambda v,_:f'{v:.3f}')
    d=fig.add_subplot(gs[2]);lim=float(np.nanquantile(np.abs(com['diff']),0.99));cm3=WET_DRY.reversed();com.plot(column='diff',ax=d,cmap=cm3,norm=TwoSlopeNorm(0,-lim,lim),linewidth=0,rasterized=True);finish_map(d,c['dep'],c['reg'],dep_lw=0.1);d.set_title('Krigé − maille la plus proche')
    hbar_colorbar(fig,d,cm3,TwoSlopeNorm(0,-lim,lim),'Différence de SWI (plus sec que la maille ← → plus humide)',fmt=lambda v,_:f'{v:+.3f}')
    v=r['holdout_validation'];e=fig.add_subplot(gs[3]);names=['Plus proche\nmaille','IDW\n(8 voisines)','Krigeage\nordinaire'];vals=[v['NN']['rmse'],v['IDW']['rmse'],v['KRIG']['rmse']];bars=e.bar(names,vals,color=['#c9c2b4','#8fb1c9',ACCENT],width=0.6)
    for bb,x in zip(bars,vals):e.text(bb.get_x()+bb.get_width()/2,x+0.001,f'{x:.4f}',ha='center',fontsize=9,color=INK)
    e.set_ylabel('RMSE (SWI uniforme d’été)');e.set_title('Validation : 10 % des mailles retirées');[e.spines[s_].set_visible(False) for s_ in ('top','right')]
    e.text(0.5,-0.2,f"{v['n_test_cells']} mailles retirées × {v['n_years']} étés ; distance médiane à la maille connue {v['median_distance_to_nearest_obs_km']:.0f} km.\nIntervalle de krigeage à 95 % : couverture réelle {100*v['KRIG']['coverage_95']:.1f} %.",transform=e.transAxes,ha='center',va='top',fontsize=8,color=MUTED)
    title_block(fig,'Estimer le SWI uniforme là où il n’existe pas','Le SWI uniforme n’existe qu’aux 8 981 mailles de 8 km ; chaque commune est estimée par krigeage ordinaire (variogramme exponentiel) avec son incertitude, plutôt que par la maille la plus proche.',SRC)
    save(fig,'interpolation_communes')

def fig_official(c):
    """Critère officiel CatNat : contrôle sur 2024 (rapport Météo-France), 2026 provisoire et série annuelle."""
    from catnat.official import annual_minimum,official_criterion
    years,ids,cube,grid=load_cube();xy=grid[['x93','y93']].to_numpy(float);full=np.isfinite(cube).all(axis=(1,2));am=np.where(full[:,None],annual_minimum(cube),np.nan);res,ranks=official_criterion(am,years)
    r24=res[2024];z=np.load(ROOT/'data/processed/official_last.npz');info=json.loads((ROOT/'reports/official_criterion.json').read_text(encoding='utf-8'))
    fig=plt.figure(figsize=(25,8.8));gs=GridSpec(1,3,figure=fig,left=0.01,right=0.985,top=0.87,bottom=0.12,wspace=0.04,width_ratios=[1,1,1.15])
    def mesh(ax,mask_layers,title):
        ax.scatter(xy[:,0],xy[:,1],s=7,marker='s',lw=0,color='#e4dfd2',rasterized=True)
        for m,col,lab,sz in mask_layers:ax.scatter(xy[m,0],xy[m,1],s=sz,marker='s',lw=0,color=col,label=lab,rasterized=True)
        c['reg'].boundary.plot(ax=ax,color=INK,lw=0.5,alpha=.6);ax.set_axis_off();ax.set_aspect('equal');ax.set_title(title);ax.legend(loc='lower left',fontsize=8.5,frameon=False,markerscale=1.6)
    a=fig.add_subplot(gs[0]);c1=r24['c1'];c2o=r24['c2']&~r24['c1']
    mesh(a,[(c2o,'#4f86a8',f'Critère 2 seul : {int(c2o.sum())} mailles',22),(c1,'#6a2c91',f'Critère 1 : {int(c1.sum())} mailles',30)],'2024 : application du critère officiel\n(le rapport Météo-France annonce 17, 34 et 47 mailles)')
    b=fig.add_subplot(gs[1]);rk=z['rank'];layers=[(rk>6,'#cdd7c4','Rang > 6 : critère non rempli',9),((rk>3)&(rk<=6),'#f1c26b','Rang 4 à 6 (période de retour ≥ 5 ans)',14),((rk>1)&(rk<=3),'#d2793b','Rang 2 ou 3 : critère 1 (≥ 10 ans)',18),(rk==1,'#7a2410','Rang 1 : record sur 30 ans',22)]
    pr=info['provisional_last_year'];mesh(b,layers,f"2026 provisoire (9 mois publiés) : {pr['c1_cells']:,} mailles au critère 1,\n{pr['rank1_cells']:,} en record".replace(',',' '))
    d=fig.add_subplot(gs[2]);ys=sorted(int(k) for k in info['by_year']);share=[info['by_year'][str(y)]['c1_or_c2']/8981*100 for y in ys]+[pr['share_territory']*100];xs=ys+[2026]
    cols=['#6a2c91']*len(ys)+['#c9a2dc'];d.bar(xs,share,color=cols,width=0.8);d.set_ylabel('Part des mailles remplissant le critère 1 ou 2 (%)');d.set_xlabel('Année')
    rec=c['tab'].groupby('year').y.sum();d2=d.twinx();d2.plot(rec.index,rec.values,color=ACCENT,lw=2.2,marker='o',ms=4,label='Communes reconnues (arrêtés)');d2.set_ylabel('Communes reconnues',color=ACCENT);d2.spines['top'].set_visible(False)
    d.spines['top'].set_visible(False);d.set_title('Part du territoire au critère officiel et communes reconnues');d.annotate('2026 : provisoire',(2026,share[-1]),xytext=(2014.5,share[-1]-6),fontsize=9,color=INK,arrowprops=dict(arrowstyle='-',color=MUTED))
    title_block(fig,'Le critère météorologique officiel du dispositif CatNat','Indice mensuel minimum du SWI uniforme, rang sur 30 ans par maille (circulaire IOME2322937C) ; critère 1 : rang ≤ 3, critère 2 : rang ≤ 6 deux années sur les quatre précédentes.',SRC)
    save(fig,'critere_officiel')

ALL={'france':fig_france,'swi':fig_swi_years,'calendar':fig_calendar,'fan':fig_fan,'nowcast':fig_nowcast,'krige':fig_krige,'bivariate':fig_bivariate,'region':fig_region,'interp':fig_interp,'official':fig_official}

def main(names=None):
    c=ctx()
    for n in names or list(ALL):ALL[n](c)

if __name__=='__main__':main(sys.argv[1:] or None)
