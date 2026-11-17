"""Écrit reports/RESULTATS.md à partir de reports/results.json (aucun chiffre saisi à la main)."""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
NAMES={'p_constante':'Fréquence constante','p_credibilite':'Fréquence commune crédibilisée','p_glm_meteo':'GLM météo','p_glm_meteo_expo':'GLM météo + exposition','p_glm_complet':'GLM complet','p_gbm_complet':'GBM complet','p_glm_argile':'GLM complet + aléa argile communal','p_gbm_argile':'GBM + aléa argile communal'}

def fr(x,d=3):return f'{x:,.{d}f}'.replace(',',' ').replace('.',',')

def main():
    r=json.loads((ROOT/'reports/results.json').read_text(encoding='utf-8'));m=r['meta'];p=r['protocol']
    lines=[f"# Résultats mesurés — fréquence de reconnaissance CatNat sécheresse",'',
      f"Table : {m['communes']} communes × années {m['years'][0]}–{m['years'][1]} ({m['rows']} lignes), fréquence moyenne {fr(100*m['positive_rate'],2)} %. Coupure des arrêtés : {m['data_cut']} ; dernière année mûre : {m['last_mature_year']}.",
      f"Validation : {p['split']} ; années de test {p['test_years'][0]}–{p['test_years'][-1]}.",'',
      '## Scores agrégés hors échantillon','','| Modèle | Log-loss | Gain vs constante | Brier | Gain Brier | AUC | Attendu | Observé |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for k,s in r['pooled'].items():
        lines.append(f"| {NAMES[k]} | {fr(s['log_loss'],4)} | {fr(100*s['log_loss_skill'],1)} % | {fr(s['brier'],4)} | {fr(100*s['brier_skill'],1)} % | {fr(s['auc'])} | {fr(s['expected'],0)} | {s['observed']} |")
    if 'pooled_recent' in r:
        a,b=r['pooled_recent']['years']
        lines+=['',f'### Sous-période {a}–{b} (mêmes modèles, historique d’apprentissage plus long)','','| Modèle | Log-loss | Gain vs constante | AUC | Attendu | Observé |','|---|---:|---:|---:|---:|---:|']
        for k,s in r['pooled_recent']['scores'].items():
            lines.append(f"| {NAMES[k]} | {fr(s['log_loss'],4)} | {fr(100*s['log_loss_skill'],1)} % | {fr(s['auc'])} | {fr(s['expected'],0)} | {s['observed']} |")
    if 'maps' in r:
        mp=r['maps'];dep=pd.read_csv(ROOT/mp['departments_file'],dtype={'departement':str})
        lines+=['','## Cartes','',f"![France](figures/carte_france_communes.png)",'',f"![Départements](figures/carte_departements.png)",'',
          f"Région détaillée : **{mp['region']}**, choisie car la plus touchée sur la période (fréquence observée {fr(100*mp['region_ranking'][0]['rate'],1)} % des communes-années). Année détaillée : {mp['region_year']}, {mp['region_observed']} communes reconnues pour {fr(mp['region_expected'],0)} attendues.",'',
          f"![Région](figures/carte_region_{mp['region_code']}.png)",'','Départements les plus sous-estimés (observé/attendu) :','','| Département | Observé | Attendu | Ratio |','|---|---:|---:|---:|']
        for _,d in dep.sort_values('ratio_obs_exp',ascending=False).head(8).iterrows():
            lines.append(f"| {d.departement} | {int(d.observed)} | {fr(d.expected,0)} | {fr(d.ratio_obs_exp,2)} |")
    lines+=['','## Observé contre attendu par année','','| Année | Observé | Crédibilité | GLM complet | GBM complet | Obs./att. GLM | AUC GLM |','|---|---:|---:|---:|---:|---:|---:|']
    by={k:pd.DataFrame(v).set_index('year') for k,v in r['by_year'].items()}
    py=pd.DataFrame(r['per_year']);auc=py[py.model=='p_glm_complet'].set_index('year').auc
    for y in by['p_glm_complet'].index:
        g=by['p_glm_complet'].loc[y]
        lines.append(f"| {y} | {int(g.observed)} | {fr(by['p_credibilite'].loc[y].expected,0)} | {fr(g.expected,0)} | {fr(by['p_gbm_complet'].loc[y].expected,0)} | {fr(g.ratio_obs_exp,2)} | {fr(auc[y])} |")
    lines+=['','## Coefficients du GLM complet (dernier apprentissage)','','Variables standardisées ; rapport de cotes pour un écart-type. Les indicateurs météo sont corrélés : lecture conjointe.','','| Variable | Coefficient | Rapport de cotes |','|---|---:|---:|']
    for c in r['glm_complet_coefficients_last_year']:lines.append(f"| `{c['variable']}` | {fr(c['coef_std'])} | {fr(c['odds_ratio_1sd'])} |")
    lines+=['','## Retard de publication des arrêtés (années, fin d’événement → publication)','','| Année d’événement | Arrêtés | Médiane | 90 % | 99 % | Max |','|---|---:|---:|---:|---:|---:|']
    for l in r['publication_lag']:
        if l['year']>=2000:lines.append(f"| {l['year']} | {int(l['count'])} | {fr(l['50%'],2)} | {fr(l['90%'],2)} | {fr(l['99%'],2)} | {fr(l['max'],2)} |")
    lines+=['','Figures : [observé/attendu](figures/observe_attendu.png), [calibration](figures/calibration.png), [retard de publication](figures/retard_publication.png).','',
      f"Environnement : Python {r['python']}, "+', '.join(f'{k} {v}' for k,v in r['versions'].items())+'.']
    (ROOT/'reports/RESULTATS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()
