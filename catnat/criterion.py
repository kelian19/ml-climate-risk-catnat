"""Critère météorologique de type « période de retour » sur le SWI uniforme trimestriel.

Reconstitution paramétrable (T = 25 ans par défaut, fenêtres glissantes de 3 mois, référence = années
antérieures uniquement). Les paramètres exacts de la circulaire ne sont pas publiés dans les données :
la reconstitution est **validée empiriquement contre les arrêtés** (voir validate_against_decrees).
"""
import numpy as np
import pandas as pd

def thresholds(q,t,T=25,min_ref=30):
    """Quantile 1/T de chaque maille × fenêtre, estimé sur les années strictement antérieures à l'indice t.
    Les années de référence incomplètes (début de série) sont écartées pour toutes les mailles."""
    ref=q[:t];ref=ref[np.isfinite(ref).all(axis=(1,2))]
    if len(ref)<min_ref:return np.full(q.shape[1:],np.nan)
    return np.quantile(ref,1/T,axis=0)

def criterion_cube(q,T=25,min_ref=30):
    """met[t,c,m] = la moyenne de la fenêtre se terminant au mois m de l'année t est sous le seuil 1/T."""
    met=np.zeros(q.shape,dtype=bool);valid=np.zeros(q.shape,dtype=bool)
    for t in range(q.shape[0]):
        thr=thresholds(q,t,T,min_ref);ok=np.isfinite(thr)&np.isfinite(q[t])
        met[t]=ok&(q[t]<thr);valid[t]=ok
    return met,valid

def return_period(q,t,min_ref=30):
    """Période de retour empirique (années) de la valeur de l'année d'indice t, par rapport aux années
    antérieures complètes : 1 / fréquence de non-dépassement, fréquence = (k + 0,5)/(n + 1)."""
    ref=q[:t];ref=ref[np.isfinite(ref).all(axis=(1,2))];n=len(ref)
    if n<min_ref:return np.full(q.shape[1:],np.nan)
    k=np.sum(ref<=q[t][None],axis=0);rp=(n+1)/(k+0.5);rp[~np.isfinite(q[t])]=np.nan
    return rp

def annual_flags(met,valid,years,months=range(3,13)):
    """Une année est « reconnaissable » pour une maille si au moins une fenêtre se terminant entre mars et
    décembre de cette année satisfait le critère."""
    idx=[m-1 for m in months]
    flag=met[:,:,idx].any(axis=2);ok=valid[:,:,idx].any(axis=2)
    return flag,ok

def validate_against_decrees(flags_commune,labels):
    """Tableau de contingence critère reconstitué × reconnaissance effective (commune-année)."""
    d=labels.merge(flags_commune,on=['insee','year'])
    tab={'commune_years':int(len(d)),'both':int(((d.flag==1)&(d.y==1)).sum()),'criterion_only':int(((d.flag==1)&(d.y==0)).sum()),
         'decree_only':int(((d.flag==0)&(d.y==1)).sum()),'neither':int(((d.flag==0)&(d.y==0)).sum())}
    tab['sensitivity']=tab['both']/max(tab['both']+tab['decree_only'],1);tab['precision']=tab['both']/max(tab['both']+tab['criterion_only'],1)
    return tab,d
