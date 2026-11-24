"""Recalcule le choix de l'intervalle unique à partir du backtest enregistré par pipeline.nowcast (sans réajuster le modèle).

Utile quand seule la règle de choix change : nowcast enregistre les rapports observé/attendu par année (backtest_by_year).
python -m pipeline.interval_choice
"""
import json
from pathlib import Path
import pandas as pd
from catnat.uncertainty import choose_interval
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=ROOT/'reports/ete_2026.json';e=json.loads(p.read_text(encoding='utf-8'))
    by=pd.DataFrame(e['backtest_by_year'])[['year','observed','expected']]
    h,rt=choose_interval(by,e['expected_recognised_communes'],0.90);e['headline_interval']=h
    rt.to_csv(ROOT/'reports/interval_realtime.csv',index=False);p.write_text(json.dumps(e,ensure_ascii=False,indent=2,default=float),encoding='utf-8')
    print({k:v for k,v in h.items() if k!='evaluation'});print(pd.DataFrame(h['evaluation']).round(3).to_string(index=False))

if __name__=='__main__':main()
