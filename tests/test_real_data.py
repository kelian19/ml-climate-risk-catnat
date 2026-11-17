"""Contrôles sur les vraies sources ; ignorés si `python -m pipeline.download` n'a pas été exécuté (cas de la CI)."""
import hashlib,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
pytestmark=pytest.mark.skipif(not (RAW/'catnat.csv').exists(),reason='données publiques non téléchargées')

def test_raw_files_match_manifest():
    manifest=json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
    for name,meta in manifest.items():
        assert hashlib.sha256((RAW/name).read_bytes()).hexdigest()==meta['sha256'],name

def test_real_table_is_complete_and_leak_free():
    from catnat.table import build_table
    t,events,meta=build_table()
    assert meta['last_mature_year']<=events.published.max().year-1
    assert t.duplicated(['insee','year']).sum()==0
    assert t.year.min()>=2006 and t.year.max()==meta['last_mature_year']
    assert meta['max_cell_distance_km']<15
    # Historique : seulement des arrêtés publiés avant l'année prédite.
    first=events.assign(year=events.start.dt.year).groupby(['insee','year']).published.min()
    sample=t[t.hist_count>0].sample(200,random_state=0)
    for _,r in sample.iterrows():
        past=first.loc[r.insee] if r.insee in first.index.get_level_values(0) else None
        known=past[(past.index<r.year)&(past.index>=r.year-10)&(past.dt.year<r.year)]
        assert len(known)==r.hist_count
