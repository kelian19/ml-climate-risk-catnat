"""Climat du SWI uniforme : tendances, fréquence des étés sévères, scénarios de sensibilité.

Ce ne sont PAS des projections climatiques (pas de modèles DRIAS/CMIP) : ce sont (i) les tendances observées
dans la réanalyse SIM depuis 1959 et (ii) des tests de sensibilité du modèle de fréquence à un déplacement du
SWI d'été, pour représenter un climat plus sec.
"""
import numpy as np
from scipy.stats import kendalltau,theilslopes

def summer_means(cube):
    """SWI moyen juin-juillet-août, année × maille."""
    return cube[:,:,5:8].mean(axis=2)

def theil_sen_trend(series,years):
    """Pente de Theil–Sen (unités/an) et p-valeur du test de Mann–Kendall pour une série annuelle."""
    ok=np.isfinite(series)
    if ok.sum()<10:return np.nan,np.nan
    slope=theilslopes(series[ok],years[ok])[0];p=kendalltau(years[ok],series[ok])[1]
    return float(slope),float(p)

def cell_trends(summer,years):
    """Tendance par maille ; renvoie (pentes, p-valeurs)."""
    n=summer.shape[1];s=np.full(n,np.nan);p=np.full(n,np.nan)
    for c in range(n):s[c],p[c]=theil_sen_trend(summer[:,c],years)
    return s,p

def severe_summer_frequency(summer,years,baseline=(1959,1988),quantile=0.10):
    """Part des mailles dont l'été est sous le quantile `quantile` de leur propre référence, par année.
    Sur la période de référence la fréquence vaut `quantile` par construction ; un écart ultérieur mesure un déplacement du climat."""
    ref=(years>=baseline[0])&(years<=baseline[1]);thr=np.nanquantile(summer[ref],quantile,axis=0)
    return np.nanmean(summer<thr[None],axis=1)

def decade_table(freq,years):
    out=[]
    for d in range(1960,2030,10):
        sel=(years>=d)&(years<d+10)&np.isfinite(freq)
        if sel.sum()>=3:out.append({'decade':f'{d}s','years':int(sel.sum()),'severe_share':float(freq[sel].mean())})
    return out

def national_trend_per_decade(summer,years):
    """Tendance de la moyenne nationale du SWI d'été (unités par décennie) et son intervalle par bootstrap d'années."""
    nat=np.nanmean(summer,axis=1);slope,p=theil_sen_trend(nat,years.astype(float))
    rng=np.random.default_rng(0);b=[]
    for _ in range(1000):
        i=np.sort(rng.integers(0,len(nat),len(nat)));b.append(theilslopes(nat[i],years[i])[0])
    lo,hi=np.quantile(b,[.05,.95]);return {'per_decade':10*slope,'ci90':[10*float(lo),10*float(hi)],'mann_kendall_p':p}
