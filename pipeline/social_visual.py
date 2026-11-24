"""Visuel carré pour les réseaux (1080 × 1350) : les 6 étapes du projet, chacune illustrée par une vignette de ses figures.

python -m pipeline.social_visual      (écrit reports/figures/social_catnat_6_etapes.png)
"""
import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,Circle
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];FIG=ROOT/'reports/figures'
INK='#1c2b27';MUTED='#6a7a72';PAPER='#fbfaf6';ACCENT='#174f43';WARN='#b24a3a';CARD='#ffffff';SAND='#efe7d6'

def crop(name,box):
    im=Image.open(FIG/f'{name}.png').convert('RGB');w,h=im.size
    return im.crop((int(box[0]*w),int(box[1]*h),int(box[2]*w),int(box[3]*h)))

def main():
    e=json.loads((ROOT/'reports/ete_2026.json').read_text(encoding='utf-8'));h=e['headline_interval']
    oc=json.loads((ROOT/'reports/official_criterion.json').read_text(encoding='utf-8'));om=json.loads((ROOT/'reports/official_model.json').read_text(encoding='utf-8'))
    si=json.loads((ROOT/'reports/spatial_interp.json').read_text(encoding='utf-8'))['holdout_validation']
    gain=100*(1-si['KRIG']['rmse']/si['NN']['rmse']);auc=om['glm_officiel']['pooled']['auc'];pr=oc['provisional_last_year']
    f=lambda x:f'{x:,.0f}'.replace(',',' ')
    steps=[('Le bon indicateur','SWI uniforme Météo-France,\nl’indice du dispositif CatNat','pro_swi_etes_secs',(0.275,0.52,0.49,0.84)),
           ('Le critère officiel',f'Reproduit à l’identique (2024).\n2026 : {f(pr["c1_cells"])} mailles sur 8 981','pro_critere_officiel',(0.345,0.17,0.605,0.775)),
           ('Combler les trous',f'Krigeage au centre des communes :\n−{gain:.0f} % d’erreur','pro_interpolation_communes',(0.015,0.20,0.265,0.82)),
           ('L’argile','121 399 polygones BRGM\nsur 34 746 communes','pro_bivarie_argile_secheresse',(0.415,0.17,0.745,0.84)),
           ('Le modèle',f'Validé en temps réel\nAUC {auc:.3f}'.replace('.',','),'pro_nowcast_2026',(0.02,0.17,0.30,0.84)),
           ('L’intervalle',f'Un seul, choisi sur le passé :\n{f(round(h["low"],-1))} – {f(round(h["high"],-1))} à {100*h["level"]:.0f} %','pro_eventail_prediction',(0.06,0.10,0.98,0.68))]
    fig=plt.figure(figsize=(10.8,13.5),dpi=100);fig.patch.set_facecolor(PAPER)
    fig.text(0.06,0.955,'SÉCHERESSE CATNAT 2026',fontsize=15,weight='bold',color=WARN,va='top')
    fig.text(0.06,0.925,'Combien de communes\nseront reconnues ?',fontsize=38,weight='bold',color=ACCENT,va='top',linespacing=1.05)
    fig.text(0.06,0.818,'6 étapes, des données Météo-France à un intervalle',fontsize=17,color=MUTED,va='top')
    W,H=0.425,0.205;xs=[0.05,0.525];ys=[0.565,0.345,0.125]
    for k,(title,text,name,box) in enumerate(steps):
        x=xs[k%2];y=ys[k//2]
        card=fig.add_axes([x,y,W,H]);card.set_axis_off();card.set_xlim(0,1);card.set_ylim(0,1)
        card.add_patch(FancyBboxPatch((0.0,0.0),1,1,boxstyle='round,pad=0,rounding_size=0.06',fc=CARD,ec='#e2e0d6',lw=1.2,transform=card.transAxes,clip_on=False))
        card.text(0.075,0.875,str(k+1),ha='center',va='center',fontsize=16,weight='bold',color='white',bbox=dict(boxstyle='circle,pad=0.38',fc=ACCENT,ec='none'))
        card.text(0.18,0.885,title,ha='left',va='center',fontsize=17,weight='bold',color=INK)
        card.text(0.05,0.76,text,ha='left',va='top',fontsize=12,color=MUTED,linespacing=1.2)
        im=crop(name,box);ax=fig.add_axes([x+0.015,y+0.010,W-0.03,H*0.56]);ax.imshow(im,aspect='auto' if name=='pro_eventail_prediction' else 'equal');ax.set_axis_off()
    fig.text(0.06,0.083,f'≈ {f(round(e["expected_recognised_communes"],-2))} communes attendues',fontsize=27,weight='bold',color=INK,va='top')
    fig.text(0.06,0.040,f'intervalle de prédiction à {100*h["level"]:.0f} % : {f(round(h["low"],-1))} – {f(round(h["high"],-1))}  ·  github.com/kelian19/ml-climate-risk-catnat',fontsize=13.5,color=MUTED,va='top')
    out=FIG/'social_catnat_6_etapes.png';fig.savefig(out,dpi=100,facecolor=PAPER);plt.close(fig);print('écrit',out.name)

if __name__=='__main__':main()
