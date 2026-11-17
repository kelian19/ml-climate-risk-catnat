"""Critère météorologique officiel du dispositif CatNat sécheresse (circulaire IOME2322937C du 29 avril 2024).

Méthode décrite dans le rapport météorologique de Météo-France (année 2024, DCSC/ACS, 27 janvier 2025) :
- pour chaque maille et chaque année, indice mensuel **minimum** de l'année (SWI uniforme mensuel) ;
- rang de cet indice parmi les `window` = 30 dernières années, la plus sèche = rang 1 ; en cas d'égalité, le rang le plus élevé
  est retenu ;
- **critère 1** : rang ≤ 3 (période de retour ≥ 10 ans) ;
- **critère 2** : rang ≤ 6 (période de retour ≥ 5 ans) **et** au moins 2 des 4 années précédentes de rang ≤ 6 (rangs calculés
  dans la même fenêtre de 30 ans).
Pour une année partielle (en cours), l'indice minimum est celui des mois déjà publiés : l'évaluation est provisoire.
"""
import numpy as np

RANK_C1=3
RANK_C2=6
WINDOW=30

def annual_minimum(cube):
    """Indice mensuel minimum de l'année par maille (année × maille) ; NaN si aucun mois n'est publié."""
    with np.errstate(all='ignore'):
        m=np.nanmin(np.where(np.isfinite(cube),cube,np.inf),axis=2)
    m[~np.isfinite(m)]=np.nan;return m

def ranks_in_window(w):
    """Rang (1 = plus sec ; égalité : rang le plus élevé) de chaque année de la fenêtre w (années × mailles)."""
    return (w[None,:,:]<=w[:,None,:]).sum(axis=1).astype(float)

def rank_last(w):
    """Rang (1 = plus sec ; égalité : rang le plus élevé) de la dernière année d'une fenêtre w (années × mailles)."""
    return (w<=w[-1][None]).sum(axis=0).astype(float)

def yearly_ranks(amin,years,window=WINDOW):
    """Rang de chaque année dans SA fenêtre de `window` ans (se terminant cette année-là), par maille ; NaN si fenêtre incomplète."""
    r={}
    for t in range(window-1,len(years)):
        w=amin[t-window+1:t+1];ok=np.isfinite(w).all(axis=0)
        if not ok.any():continue
        rk=rank_last(np.where(ok[None],w,0.));rk[~ok]=np.nan;r[int(years[t])]=rk
    return r

def criteria_from_ranks(ranks,year):
    """Critères 1 et 2 de l'année `year` à partir des rangs annuels (chacun dans sa propre fenêtre de 30 ans).

    Contrôle : 2024 donne 17 mailles au critère 1 et 34 au critère 2 (47 au moins un des deux), comme le rapport de Météo-France.
    Le rapport n'est pas explicite ; ce sont les rangs de PR_AAAA publiés l'année concernée, donc dans leur propre fenêtre,
    qui reproduisent ses chiffres (une fenêtre commune donnerait 28 mailles)."""
    r0=ranks[year];prev=[ranks.get(year-k) for k in range(1,5)]
    if any(p is None for p in prev):return None
    n5=np.sum([p<=RANK_C2 for p in prev],axis=0).astype(float);ok=np.isfinite(r0)&np.all([np.isfinite(p) for p in prev],axis=0)
    c1=(r0<=RANK_C1)&np.isfinite(r0);c2=(r0<=RANK_C2)&(n5>=2)&ok
    return {'rank':r0,'c1':c1,'c2':c2,'n_pr5_prev4':np.where(ok,n5,np.nan)}

def official_criterion(amin,years,window=WINDOW):
    """Critères pour chaque année évaluable (critère 2 : à partir de la 4e année après la première fenêtre complète)."""
    ranks=yearly_ranks(amin,years,window);out={}
    for y in ranks:
        c=criteria_from_ranks(ranks,y)
        if c is not None:out[y]=c
    return out,ranks

def provisional_ranks(amin_partial,amin_history,ranks,year,window=WINDOW):
    """Évaluation provisoire d'une année en cours : l'indice minimum des mois publiés est classé parmi les window − 1 années précédentes."""
    w=np.vstack([amin_history[-(window-1):],amin_partial[None]]);ok=np.isfinite(w).all(axis=0)
    rk=rank_last(np.where(ok[None],w,0.));rk[~ok]=np.nan;r=dict(ranks);r[year]=rk;return criteria_from_ranks(r,year)

FEATURES_OFFICIEL=['off_rank_log','off_c1','off_c2']

def official_features(cube,years,ids,last_month=12):
    """Variables maille × année issues du critère officiel, avec les mois ≤ last_month (cohérence avec l'année en cours).

    off_rank_log = log du rang de l'indice minimum dans la fenêtre de 30 ans (0 = record) ; off_c1, off_c2 = critères 1 et 2.
    Avant la première année évaluable (critère 2 : 1992) le critère 2 vaut 0 ; avant la première fenêtre complète (1988) la ligne manque."""
    import pandas as pd
    amin=annual_minimum(cube[:,:,:last_month]);ranks=yearly_ranks(amin,years);rows=[]
    for y,rk in ranks.items():
        c=criteria_from_ranks(ranks,y)
        c1=(rk<=RANK_C1) if c is None else c['c1'];c2=np.zeros(len(ids),bool) if c is None else c['c2']
        rows.append(pd.DataFrame({'cell':ids,'year':y,'off_rank_log':np.log(rk),'off_c1':c1.astype(float),'off_c2':c2.astype(float)}))
    return pd.concat(rows,ignore_index=True)
