"""Variable à expliquer : une commune est « reconnue » pour l'année t si au moins un arrêté CatNat
sécheresse porte sur un événement débutant en t. La reconnaissance est publiée avec un retard de
plusieurs mois à plusieurs années : l'observation la plus récente est donc incomplète (censure à droite)."""
import numpy as np
import pandas as pd

def last_mature_year(events,window=5,quantile=0.99):
    """Dernière année d'événement dont les arrêtés peuvent être considérés comme publiés.

    Le retard (publication − fin d'événement) est mesuré sur `window` années de référence assez anciennes
    pour être quasi complètes (de cut−2−window à cut−3, cut étant l'année de la dernière publication) ;
    une année L est mûre si la date de coupure dépasse 31/12/L d'au moins le quantile de ce retard."""
    cut=events.published.max()
    lag=(events.published-events.end).dt.days/365.25
    y=events.start.dt.year
    ref=(y>cut.year-3-window)&(y<=cut.year-3)
    if not ref.any():raise ValueError('Aucune année de référence pour estimer le retard de publication.')
    q=float(np.quantile(lag[ref],quantile))
    for year in range(int(y.max()),int(y.min())-1,-1):
        if (cut-pd.Timestamp(year,12,31)).days/365.25>=q:return year
    raise ValueError('Aucune année mûre.')

def publication_lag_table(events):
    """Retard de publication (années) par année de début d'événement, pour documentation."""
    lag=(events.published-events.end).dt.days/365.25
    return lag.groupby(events.start.dt.year).describe(percentiles=[.5,.9,.99])[['count','50%','90%','99%','max']]

def build_labels(events,communes,years):
    """Grille complète commune × année avec l'indicateur de reconnaissance et le nombre d'arrêtés."""
    ev=events[events.insee.isin(communes.code)].copy();ev['year']=ev.start.dt.year
    n=ev.groupby(['insee','year']).size().rename('n_arretes')
    grid=pd.MultiIndex.from_product([communes.code,list(years)],names=['insee','year']).to_frame(index=False)
    grid=grid.merge(n.reset_index(),on=['insee','year'],how='left')
    grid['n_arretes']=grid.n_arretes.fillna(0).astype(int);grid['y']=(grid.n_arretes>0).astype(int)
    return grid

def history_counts(events,communes,years,window=10):
    """Nombre d'années récentes (t−window … t−1) avec reconnaissance, **connue au 1er janvier t** :
    seuls les arrêtés publiés avant cette date comptent, pour ne pas utiliser une information indisponible."""
    ev=events[events.insee.isin(communes.code)].copy();ev['year']=ev.start.dt.year
    first=ev.groupby(['insee','year']).published.min().reset_index();first['pub_year']=first.published.dt.year
    parts=[]
    for t in years:
        sel=first[(first.pub_year<t)&(first.year<t)&(first.year>=t-window)]
        parts.append(sel.groupby('insee').size().rename('hist_count').reset_index().assign(year=t))
    out=pd.concat(parts,ignore_index=True)
    return out
