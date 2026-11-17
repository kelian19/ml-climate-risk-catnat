"""Génère docs/latex/tables.tex (macros de tableaux) depuis les résultats JSON : aucun chiffre saisi à la main."""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports'
NAMES={'p_constante':'Fréquence constante','p_credibilite':'Fréquence communale crédibilisée','p_glm_meteo':'GLM, SWI uniforme','p_glm_meteo_expo':'GLM, SWI uniforme + exposition','p_glm_complet':'GLM complet (+ historique publié)','p_gbm_complet':'Gradient boosting complet'}
FNAMES={'p_persistance':'Persistance (SWI d’été précédent)','p_climatologie':'Climatologie de la maille','p_ridge':'Régression ridge','p_gbm':'Gradient boosting','p_rf':'Forêt aléatoire'}

def fr(x,d=2):
    t=f'{abs(x):,.{d}f}'.replace(',','\\,').replace('.','{,}')
    return ('$-$' if x<0 and float(f'{abs(x):.{d}f}')!=0 else '')+t
def macro(name,body):return f'\\newcommand{{\\{name}}}{{%\n{body}\n}}\n'
def tab(cols,header,rows):return '\\begin{tabular}{'+cols+'}\\toprule\n'+header+' \\\\\\midrule\n'+'\n'.join(r+' \\\\' for r in rows)+'\n\\bottomrule\\end{tabular}'

def main():
    r=json.loads((R/'results.json').read_text(encoding='utf-8'));s=json.loads((R/'swi_study.json').read_text(encoding='utf-8'));e=json.loads((R/'ete_2026.json').read_text(encoding='utf-8'))
    m=r['meta'];out='% Fichier généré par python -m pipeline.make_tables ; ne pas modifier à la main.\n'
    out+=macro('metaTable',f"{m['communes']:,} communes, {m['years'][0]}--{m['years'][1]}".replace(',','\\,')+f", {m['rows']:,} lignes".replace(',','\\,'))
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
        rows.append(f"{T} ans & {c['both']:,} & {c['criterion_only']:,} & {c['decree_only']:,} & {fr(100*c['sensitivity'],1)}\\,\\% & {fr(100*c['precision'],1)}\\,\\%".replace(',','\\,'))
    out+=macro('tabCriterion',tab('lrrrrr','Période de retour & Les deux & Critère seul & Arrêté seul & Sensibilité & Précision',rows))
    sev=e['severity'];rows=[f"{x['year']} & {fr(x['swi_jja_z'],2)} & {fr(x['rp_max_log'],2)} & {int(x['communes_reconnues']):,}".replace(',','\\,') for x in e['comparison_years']]
    rows.insert(0,f"\\textbf{{2026}} & \\textbf{{{fr(sev['swi_jja_z_mean'],2)}}} & \\textbf{{{fr(sev['rp_max_log_mean'],2)}}} & estimation")
    out+=macro('tabSeverity',tab('rrrr','Année & Anomalie JJA moyenne & ln(période de retour) & Communes reconnues',rows))
    rows=[f"{x['region']} & {fr(100*x['rate'],1)}\\,\\% & {fr(x['expected'],0)}" for x in e['regions'][:8]]
    out+=macro('tabRegions2026',tab('lrr','Région & Part attendue & Communes attendues',rows))
    out+=macro('nowcastSummary',f"{fr(e['expected_recognised_communes'],0)} communes attendues ; fourchette empirique {fr(e['empirical_range'][0],0)}--{fr(e['empirical_range'][1],0)}")
    dep=pd.read_csv(R/'departements.csv',dtype={'departement':str}).sort_values('ratio_obs_exp',ascending=False).head(8)
    rows=[f"{d.departement} & {int(d.observed)} & {fr(d.expected,0)} & {fr(d.ratio_obs_exp,2)}" for d in dep.itertuples()]
    out+=macro('tabDept',tab('rrrr','Département & Observé & Attendu & Rapport',rows))
    lag=[l for l in r['publication_lag'] if l['year'] in (2000,2005,2010,2015,2018,2020,2022)]
    out+=macro('tabLag',tab('rrrrr','Année d’événement & Arrêtés & Médiane & 99\,\% & Maximum',[f"{int(l['year'])} & {int(l['count'])} & {fr(l['50%'],2)} & {fr(l['99%'],2)} & {fr(l['max'],2)}" for l in lag]))
    (ROOT/'docs/latex').mkdir(parents=True,exist_ok=True);(ROOT/'docs/latex/tables.tex').write_text(out,encoding='utf-8');print('tables.tex écrit')

if __name__=='__main__':main()
