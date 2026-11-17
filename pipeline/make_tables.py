"""Génère docs/latex/tables.tex (macros de tableaux) depuis les résultats JSON : aucun chiffre saisi à la main."""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports'
NAMES={'p_constante':'Fréquence constante','p_credibilite':'Fréquence communale crédibilisée','p_glm_meteo':'GLM, SWI uniforme','p_glm_meteo_expo':'GLM, SWI uniforme + exposition','p_glm_complet':'GLM complet (+ historique publié)','p_gbm_complet':'Gradient boosting complet','p_glm_argile':'GLM complet + aléa argile communal','p_gbm_argile':'Gradient boosting + aléa argile communal'}
FNAMES={'p_persistance':'Persistance (SWI d’été précédent)','p_climatologie':'Climatologie de la maille','p_ridge':'Régression ridge','p_gbm':'Gradient boosting','p_rf':'Forêt aléatoire'}

def fr(x,d=2):
    t=f'{abs(x):,.{d}f}'.replace(',','\\,').replace('.','{,}')
    return ('$-$' if x<0 and float(f'{abs(x):.{d}f}')!=0 else '')+t
def ci(n):return f'{int(n):,}'.replace(',',chr(92)+',')
def macro(name,body):return f'\\newcommand{{\\{name}}}{{%\n{body}\n}}\n'
def tab(cols,header,rows):return '\\begin{tabular}{'+cols+'}\\toprule\n'+header+' \\\\\\midrule\n'+'\n'.join(r+' \\\\' for r in rows)+'\n\\bottomrule\\end{tabular}'

def main():
    r=json.loads((R/'results.json').read_text(encoding='utf-8'));s=json.loads((R/'swi_study.json').read_text(encoding='utf-8'));e=json.loads((R/'ete_2026.json').read_text(encoding='utf-8'))
    m=r['meta'];out='% Fichier généré par python -m pipeline.make_tables ; ne pas modifier à la main.\n'
    out+=macro('metaTable',f"{ci(m['communes'])} communes, {m['years'][0]}--{m['years'][1]}, {ci(m['rows'])} lignes")
    rows=[f"{NAMES[k]} & {fr(v['log_loss'],4)} & {fr(100*v['log_loss_skill'],1)}\\,\\% & {fr(v['brier'],4)} & {fr(v['auc'],3)} & {fr(v['expected'],0)}" for k,v in r['pooled'].items()]
    out+=macro('tabModels',tab('lrrrrr','Modèle & Log-loss & Gain & Brier & AUC & Attendu',rows))
    rec=r['pooled_recent'];rows=[f"{NAMES[k]} & {fr(v['log_loss'],4)} & {fr(100*v['log_loss_skill'],1)}\\,\\% & {fr(v['auc'],3)} & {fr(v['expected'],0)}" for k,v in rec['scores'].items()]
    out+=macro('tabModelsRecent',tab('lrrrr','Modèle & Log-loss & Gain & AUC & Attendu',rows))
    by={k:pd.DataFrame(v).set_index('year') for k,v in r['by_year'].items()};py=pd.DataFrame(r['per_year']);auc=py[py.model=='p_glm_complet'].set_index('year').auc
    rows=[f"{y} & {int(by['p_glm_complet'].loc[y].observed)} & {fr(by['p_credibilite'].loc[y].expected,0)} & {fr(by['p_glm_complet'].loc[y].expected,0)} & {fr(by['p_glm_complet'].loc[y].ratio_obs_exp,2)} & {fr(auc[y],3)}" for y in by['p_glm_complet'].index if y>=2005]
    out+=macro('tabByYear',tab('rrrrrr','Année & Observé & Crédibilité & GLM & Obs./att. & AUC',rows))
    rows=[f"\\texttt{{{c['variable'].replace('_','\\_')}}} & {fr(c['coef_std'],3)} & {fr(c['odds_ratio_1sd'],3)}" for c in r['glm_complet_coefficients_last_year']]
    out+=macro('tabCoef',tab('lrr','Variable & Coefficient & Rapport de cotes (1 écart-type)',rows))
    f=s['forecast']
    def ftab(key):
        return tab('lrrrrr','Modèle & RMSE & MAE & Corrél. & RMSE nat. & Corrél. nat.',[f"{FNAMES[x['model']]} & {fr(x['rmse'],3)} & {fr(x['mae'],3)} & {fr(x['corr'],3)} & {fr(x['national_rmse'],3)} & {fr(x['national_corr'],2)}" for x in f[key]])
    out+=macro('tabForecastAll',ftab('scores'));out+=macro('tabForecastDry',ftab('scores_dry_years'))
    g=s['geostat'];rows=[f"{k} & {fr(1e3*v['nugget'],2)} & {fr(1e3*v['psill'],2)} & {fr(v['range']/1000,0)} & {fr(1e3*v['wrmse'],3)}" for k,v in g['fits'].items()]
    out+=macro('tabVariogram',tab('lrrrr','Modèle & Pépite ($\\times10^{-3}$) & Palier ($\\times10^{-3}$) & Portée (km) & Erreur pond. ($\\times10^{-3}$)',rows))
    rows=[f"{lab} & {fr(c['rmse'],4)} & {fr(c['mae'],4)} & {fr(100*c['coverage_95'],1)}\\,\\% & {fr(c['std_standardized_error'],2)} & {c['n']}" for lab,c in [('Blocs de 100 km',g['block_cv_100km']),('Blocs de 25 km',g['block_cv_25km'])]]
    out+=macro('tabKriging',tab('lrrrrr','Validation & RMSE & MAE & Couverture 95\\,\\% & Écart-type erreur std. & Points',rows))
    rows=[]
    for T,c in s['criterion'].items():
        rows.append(f"{T} ans & {ci(c['both'])} & {ci(c['criterion_only'])} & {ci(c['decree_only'])} & {fr(100*c['sensitivity'],1)}"+chr(92)+","+chr(92)+f"% & {fr(100*c['precision'],1)}"+chr(92)+","+chr(92)+"%")
    out+=macro('tabCriterion',tab('lrrrrr','Période de retour & Les deux & Critère seul & Arrêté seul & Sensibilité & Précision',rows))
    sev=e['severity'];rows=[f"{x['year']} & {fr(x['swi_jja_z'],2)} & {fr(x['rp_max_log'],2)} & {ci(x['communes_reconnues'])}" for x in e['comparison_years']]
    rows.insert(0,f"\\textbf{{2026}} & \\textbf{{{fr(sev['swi_jja_z_mean'],2)}}} & \\textbf{{{fr(sev['rp_max_log_mean'],2)}}} & estimation")
    out+=macro('tabSeverity',tab('rrrr','Année & Anomalie JJA moyenne & ln(période de retour) & Communes reconnues',rows))
    rows=[f"{x['region']} & {fr(100*x['rate'],1)}\\,\\% & {fr(x['expected'],0)}" for x in e['regions'][:8]]
    out+=macro('tabRegionsNow',tab('lrr','Région & Part attendue & Communes attendues',rows))
    out+=macro('nowcastSummary',f"{fr(e['expected_recognised_communes'],0)} communes attendues ; fourchette empirique {fr(e['empirical_range'][0],0)}--{fr(e['empirical_range'][1],0)}")
    dep=pd.read_csv(R/'departements.csv',dtype={'departement':str}).sort_values('ratio_obs_exp',ascending=False).head(8)
    rows=[f"{d.departement} & {int(d.observed)} & {fr(d.expected,0)} & {fr(d.ratio_obs_exp,2)}" for d in dep.itertuples()]
    out+=macro('tabDept',tab('rrrr','Département & Observé & Attendu & Rapport',rows))
    lag=[l for l in r['publication_lag'] if l['year'] in (2000,2005,2010,2015,2018,2020,2022)]
    out+=macro('tabLag',tab('rrrrr','Année d’événement & Arrêtés & Médiane & 99\,\% & Maximum',[f"{int(l['year'])} & {int(l['count'])} & {fr(l['50%'],2)} & {fr(l['99%'],2)} & {fr(l['max'],2)}" for l in lag]))
    pi=e['prediction_interval_80'];pj=e['prediction_interval_90'];ei=e['estimation_interval_90'];cv=e['prediction_interval_loo_coverage']
    rows=[f"Nombre attendu de communes reconnues & {fr(e['expected_recognised_communes'],0)}",f"Intervalle à 90\,\% de l'estimation (bootstrap par années) & {fr(ei[0],0)}--{fr(ei[1],0)}",
          f"Intervalle de prédiction à 80\,\% (backtest) & {fr(pi[0],0)}--{fr(pi[1],0)}",f"Intervalle de prédiction à 90\,\% (backtest) & {fr(pj[0],0)}--{fr(pj[1],0)}",
          f"Couverture une année laissée de côté ({cv['years']} ans), 80\,\% / 90\,\% & {fr(100*cv['80'],0)}\,\% / {fr(100*cv['90'],0)}\,\%"]
    out+=macro('tabIntervals',tab('lr','Résultat 2026 & Valeur',rows))
    o=json.loads((R/'old_score_check.json').read_text(encoding='utf-8'))
    rows=[f"{lab} & {fr(o[k]['spearman'],2)} & {fr(o[k]['ci90'][0],2)}--{fr(o[k]['ci90'][1],2)}" for lab,k in [('Score composite d’origine','score_catnat'),('Aléa argile BRGM seul','arg_norm'),('Part de jours secs seule','dry_norm'),('Modèle de fréquence','modele_frequence')]]
    out+=macro('tabOldScore',tab('lrr','Indicateur & Spearman & Intervalle à 90\,\%',rows))
    c=json.loads((R/'climate.json').read_text(encoding='utf-8'));nt=c['national_trend']
    rows=[f"{d['decade']} & {d['years']} & {fr(100*d['severe_share'],1)}\,\%" for d in c['severe_summer_share_by_decade']]
    out+=macro('tabClimateDecades',tab('lrr','Décennie & Années & Mailles sous le décile de 1959--1988',rows))
    out+=macro('climateTrend',f"{fr(nt['per_decade'],3)} par décennie (intervalle à 90\,\% : {fr(nt['ci90'][0],3)} à {fr(nt['ci90'][1],3)} ; Mann--Kendall $p={fr(nt['mann_kendall_p'],3)}$)")
    rows=[f"{x['base_year']} & {fr(x['shift'],2)} & {fr(x['shift_sd'],2)} & {fr(x['expected_communes'],0)} & {x['observed_communes']}" for x in c['sensitivity']]
    out+=macro('tabSensitivity',tab('rrrrr','Année de base & Déplacement du SWI & En écarts-types & Communes attendues & Observé',rows))
    out+=macro('geoMoran',f"{fr(g['moran_I'],2)} (p = {fr(g['moran_p'],3)}, {g['n_cells']} mailles, été {g['year']})");out+=macro('geoBest',f"{g['best_model']} (portée {fr(g['fits'][g['best_model']]['range']/1000,0)}\,km)")
    si=json.loads((R/'spatial_interp.json').read_text(encoding='utf-8'));hv=si['holdout_validation']
    rows=[f"{lab} & {fr(hv[k]['rmse'],4)} & {fr(hv[k]['mae'],4)} & {fr(hv[k]['bias'],4)} & "+(f"{fr(100*hv[k]['coverage_95'],1)}"+chr(92)+","+chr(92)+"%" if 'coverage_95' in hv[k] else '--') for lab,k in [('Maille la plus proche','NN'),('Pondération inverse (IDW)','IDW'),('Krigeage ordinaire','KRIG')]]
    out+=macro('tabInterp',tab('lrrrr','Méthode & RMSE & MAE & Biais & Couverture 95'+chr(92)+','+chr(92)+'%',rows))
    me=si['model_effect'];rows=[f"{lab} & {fr(100*me[k]['log_loss_skill'],2)}"+chr(92)+","+chr(92)+f"% & {fr(me[k]['auc'],4)}" for lab,k in [('Maille la plus proche','plus_proche_maille'),('SWI krigé au centre des communes','krigeage')]]
    out+=macro('tabInterpModel',tab('lrr','Source du SWI (GLM complet, 1995--2022) & Gain de log-loss & AUC',rows))
    out+=macro('interpSummary',f"variogramme exponentiel standardisé (pépite {fr(100*si['standardized_variogram']['nugget'],1)}"+chr(92)+","+chr(92)+f"%) ; centre de commune à {fr(si['median_distance_commune_to_nearest_cell_km'],1)}"+chr(92)+f",km de la maille la plus proche en médiane ({fr(si['p95_distance_km'],1)}"+chr(92)+f",km au 95$^e$ centile) ; {hv['n_test_cells']} mailles retirées, {hv['n_years']} étés")
    # Critère officiel, comparaison de modèles, blocs spatiaux
    oc=json.loads((R/'official_criterion.json').read_text(encoding='utf-8'));om=json.loads((R/'official_model.json').read_text(encoding='utf-8'));mc=json.loads((R/'ml_compare.json').read_text(encoding='utf-8'))
    c24=oc['check_2024_vs_report']['ours'];rep=oc['check_2024_vs_report']['report']
    out+=macro('tabOfficialCheck',tab('lrr','Mailles, année 2024 & Rapport Météo-France & Notre application',[f"Critère 1 & {rep['c1']} & {c24['c1']}",f"Critère 2 & {rep['c2']} & {c24['c2']}",f"Au moins un des deux & {rep['total']} & {c24['c1_or_c2']}"]))
    rows=[f"{d['critère'].replace('critère','Critère')} & {ci(d['communes_critère'])} & {fr(100*d['sensibilité'],1)}\\,\\% & {fr(100*d['précision'],1)}\\,\\%" for d in oc['vs_decrees']]
    out+=macro('tabOfficialDecrees',tab('lrrr','Critère officiel appliqué à la maille de la commune & Communes--années & Sensibilité & Précision',rows))
    pr=oc['provisional_last_year']
    out+=macro('officialSummary',f"{ci(pr['c1_cells'])} mailles sur 8\\,981 remplissent déjà le critère 1 en {pr['year']} ({pr['months_published']} mois publiés), dont {ci(pr['rank1_cells'])} en record sur 30 ans ; au moins un des deux critères : {fr(100*pr['share_territory'],1)}\\,\\% du territoire. AUC du rang seul contre les arrêtés : {fr(oc['auc_rank_vs_decrees'],3)}")
    ON={'credibilite':'Fréquence communale crédibilisée','glm_argile':'GLM + aléa argile communal','glm_officiel':'GLM + aléa argile + critère officiel','gbm_officiel':'Gradient boosting + critère officiel'}
    rows=[f"{ON[k]} & {fr(100*v['pooled']['log_loss_skill'],1)}\\,\\% & {fr(v['pooled']['auc'],3)} & {fr(100*v['recent_2010_2022']['log_loss_skill'],1)}\\,\\%" for k,v in om.items()]
    out+=macro('tabOfficialModel',tab('lrrr','Modèle & Gain 1995--2022 & AUC & Gain 2010--2022',rows))
    MN={'credibilite':'Fréquence communale crédibilisée','glm_argile':'GLM','gbm_argile':'Gradient boosting','rf_argile':'Forêt aléatoire','ensemble':'Ensemble (moyenne des trois)'}
    rows=[f"{MN[k]} & {fr(100*v['pooled']['log_loss_skill'],1)}\\,\\% & {fr(v['pooled']['auc'],3)} & {fr(100*v['recent_2010_2022']['log_loss_skill'],1)}\\,\\% & {fr(v['ratio_obs_exp_median'],2)}" for k,v in mc['models'].items()]
    out+=macro('tabMLCompare',tab('lrrrr','Modèle (mêmes variables, argile communale) & Gain 1995--2022 & AUC & Gain 2010--2022 & Obs./att. médian',rows))
    SN={'glm_argile':'GLM','gbm_argile':'Gradient boosting'};rows=[]
    for k,v in mc['spatial_blocks'].items():
        t=v['time_only_same_years'];rows.append(f"{SN[k]} & {fr(100*t['log_loss_skill'],1)}\\,\\% & {fr(t['auc'],3)} & {fr(100*v['pooled']['log_loss_skill'],1)}\\,\\% & {fr(v['pooled']['auc'],3)}")
    out+=macro('tabSpatialBlocks',tab('lrrrr','Modèle & Gain (temps seul) & AUC (temps seul) & Gain (blocs retirés) & AUC (blocs retirés)',rows))
    (ROOT/'docs/latex').mkdir(parents=True,exist_ok=True);(ROOT/'docs/latex/tables.tex').write_text(out,encoding='utf-8');print('tables.tex écrit')

if __name__=='__main__':main()
