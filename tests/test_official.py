"""Critère officiel CatNat sécheresse (circulaire IOME2322937C) : règles de rang, égalités, critère 2, contrôle sur 2024."""
from pathlib import Path
import numpy as np
import pytest
from catnat.official import annual_minimum,rank_last,yearly_ranks,criteria_from_ranks,official_criterion,RANK_C1

def test_annual_minimum_ignores_missing_months():
    c=np.full((2,1,12),0.5);c[0,0,3]=0.1;c[1,0,:5]=[0.4,0.3,0.2,np.nan,0.6];c[1,0,5:]=np.nan
    m=annual_minimum(c);assert m[0,0]==0.1 and m[1,0]==0.2
    assert np.isnan(annual_minimum(np.full((1,1,12),np.nan))[0,0])

def test_rank_ties_take_highest_rank():
    # exemple du rapport : la plus basse valeur est atteinte deux fois -> les deux années ont le rang 2 ; la suivante le rang 3
    w=np.array([[0.2],[0.2],[0.5]]);assert rank_last(w[[0,2,1]])[0]==2 and rank_last(w[[1,2,0]])[0]==2
    assert rank_last(np.array([[0.2],[0.2],[0.3]]))[0]==3

def test_criterion_1_is_rank_le_3_of_30():
    rng=np.random.default_rng(0);amin=rng.uniform(0.3,0.9,size=(40,500));years=np.arange(1980,2020)
    res,ranks=official_criterion(amin,years);r=ranks[2019]
    assert (r[res[2019]['c1']]<=RANK_C1).all() and (r[~res[2019]['c1']]>RANK_C1).all()
    # sous l'hypothèse d'échangeabilité, P(rang ≤ 3 sur 30) = 3/30
    assert abs(np.mean([ranks[y]<=3 for y in range(2012,2020)])-0.1)<0.03

def test_criterion_2_uses_each_previous_year_in_its_own_window():
    years=np.arange(1980,2020);amin=np.tile(np.linspace(0.9,0.3,40)[:,None],(1,3))   # série strictement décroissante : chaque année est un record
    amin[:,1]=0.6;amin[-1,1]=0.2                                                       # maille 1 : seule la dernière année est sèche
    res,ranks=official_criterion(amin,years);c=res[2019]
    assert c['c1'].tolist()==[True,True,True] and c['c2'].tolist()==[True,False,True]
    # chaque année précédente est un record dans sa propre fenêtre (rang 1) pour la maille 0
    assert all(ranks[y][0]==1 for y in (2015,2016,2017,2018))

def test_first_years_not_evaluable():
    amin=np.random.default_rng(1).uniform(size=(40,5));years=np.arange(1980,2020);res,ranks=official_criterion(amin,years)
    assert min(ranks)==2009 and min(res)==2013   # fenêtre de 30 ans, puis 4 années précédentes pour le critère 2

@pytest.mark.skipif(not (Path(__file__).resolve().parents[1]/'data/raw/swi_mailles.csv').exists(),reason='données SWI absentes')
def test_matches_meteo_france_report_2024():
    """Le rapport Météo-France 2024 annonce 17 mailles au critère 1, 34 au critère 2 et 47 au moins un des deux."""
    from catnat.swi import load_cube
    years,ids,cube,grid=load_cube();full=np.isfinite(cube).all(axis=(1,2));am=np.where(full[:,None],annual_minimum(cube),np.nan)
    res,_=official_criterion(am,years);r=res[2024]
    assert int(r['c1'].sum())==17 and int(r['c2'].sum())==34 and int((r['c1']|r['c2']).sum())==47
