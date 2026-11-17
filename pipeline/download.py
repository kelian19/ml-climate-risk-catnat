"""Téléchargement reproductible des sources publiques, avec empreintes SHA-256.

Aucune donnée brute n'est versionnée (data/raw/ est ignoré). Le manifeste
data/manifest.json enregistre URL, taille et empreinte : un second téléchargement
dont l'empreinte diffère est refusé (revue de version requise) sauf --update.
"""
import argparse,hashlib,json,sys,time,urllib.request
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw';MANIFEST=ROOT/'data/manifest.json'
SIM_URL='https://meteofrance.s3.sbg.io.cloud.ovh.net/data/REF_CC/SIM_MENS/MENS_SIM2_{year}.csv.gz'
FIRST_YEAR,LAST_YEAR=1958,2025
CONTOURS='https://contours-administratifs.s3.rbx.io.cloud.ovh.net/2026/geojson/communes-100m.geojson.gz'
SHAPE_BASE='https://static.data.gouv.fr/resources/donnees-changement-climatique-sim-mensuelle'
DATAGOUV='https://www.data.gouv.fr/api/1/datasets/{slug}/'
CATNAT_SLUG='arretes-de-catastrophe-naturelle-par-commune'
RGA_SLUG='exposition-des-maisons-individuelles-au-phenomene-de-retrait-gonflement-des-argiles-rga'
SWI_SLUGS=('donnees-mensuelles-de-suivi-dindice-dhumidite-des-sols','donnees-mensuelles-de-reference-dindice-dhumidite-des-sols-pour-le-dispositif-catnat')
COMMUNES='https://geo.api.gouv.fr/communes?fields=code,nom,codeDepartement,codeEpci,population,surface,centre&format=json&geometry=centre'

def fetch_json(url):
    with urllib.request.urlopen(url,timeout=60) as r:return json.load(r)

def sources():
    """Liste (nom de fichier, URL) ; les URL de data.gouv sont résolues par l'API du catalogue."""
    out=[(f'MENS_SIM2_{y}.csv.gz',SIM_URL.format(year=y)) for y in range(FIRST_YEAR,LAST_YEAR+1)]
    sim=fetch_json(DATAGOUV.format(slug='donnees-changement-climatique-sim-mensuelle'))
    for res in sim['resources']:
        if res['title'].startswith('SHP_SIM_FRANCE.') and res['format'] in ('shp','shx','dbf','cpg'):out.append((res['title'],res['url']))
    out.append(('catnat.csv',next(r['url'] for r in fetch_json(DATAGOUV.format(slug=CATNAT_SLUG))['resources'] if r['title']=='catnat.csv')))
    rga=fetch_json(DATAGOUV.format(slug=RGA_SLUG))['resources']
    epci=next(r for r in rga if r['format']=='csv' and 'EPCI' in r['title'])
    out.append(('rga_epci.csv',epci['url']))
    out.append(('communes.json',COMMUNES))
    out.append(('communes-100m.geojson.gz',CONTOURS))
    # SWI uniforme Météo-France : suivi mensuel 1958→ et données de référence du dispositif CatNat.
    for slug in SWI_SLUGS:
        for res in fetch_json(DATAGOUV.format(slug=slug))['resources']:
            if res['format'] not in ('csv.gz','csv','pdf'):continue
            name=res['url'].rsplit('/',1)[-1]
            # Noms courts : les chemins Windows sont limités à 260 caractères.
            if 'mailles' in name:name='swi_mailles.csv'
            elif name.endswith('.pdf'):name='swi_presentation.pdf'
            out.append((name,res['url']))
    return out

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def download(url,target,retries=3):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url,timeout=120) as r,open(target,'wb') as f:
                while True:
                    chunk=r.read(1<<20)
                    if not chunk:break
                    f.write(chunk)
            return
        except OSError:
            if attempt==retries-1:raise
            time.sleep(3*(attempt+1))

def main(update=False):
    RAW.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {}
    for name,url in sources():
        target=RAW/name
        if not target.exists():
            print('téléchargement',name);download(url,target)
        digest=sha256(target);known=manifest.get(name)
        if known and known['sha256']!=digest and not update:
            sys.exit(f'{name} : empreinte différente de celle du manifeste ; revue de version requise (option --update pour accepter).')
        if not known or update:manifest[name]={'url':url,'sha256':digest,'bytes':target.stat().st_size,'downloaded':date.today().isoformat()}
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
    print(f'{len(manifest)} fichiers vérifiés ; manifeste : {MANIFEST.relative_to(ROOT)}')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--update',action='store_true');main(ap.parse_args().update)
