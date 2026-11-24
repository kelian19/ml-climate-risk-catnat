"""Carrousel LinkedIn (PDF, 8 pages 1080 × 1350) : une idée par page, les vraies figures du projet, chiffres lus dans les rapports.

python -m pipeline.social_carousel     (écrit reports/figures/carrousel_catnat.pdf)
"""
import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];FIG=ROOT/'reports/figures';R=ROOT/'reports'
INK='#1c2b27';MUTED='#6a7a72';PAPER='#fbfaf6';ACCENT='#174f43';WARN='#b24a3a'
N=8

def f(x,d=0):return f'{x:,.{d}f}'.replace(',',' ').replace('.',',') if d else f'{x:,.0f}'.replace(',',' ')

def crop(name,box):
    im=Image.open(FIG/f'{name}.png').convert('RGB');w,h=im.size
    return im.crop((int(box[0]*w),int(box[1]*h),int(box[2]*w),int(box[3]*h)))

def side(a,b):
    h=max(a.height,b.height);b=b.resize((int(b.width*a.height/b.height),a.height));out=Image.new('RGB',(a.width+b.width,a.height),PAPER);out.paste(a,(0,0));out.paste(b,(a.width,0));return out

def frame(pdf,page,kicker,title,text,image=None,big=None,big_color=ACCENT,img_box=(0.06,0.20,0.88,0.48)):
    fig=plt.figure(figsize=(10.8,13.5),dpi=100);fig.patch.set_facecolor(PAPER)
    fig.text(0.06,0.955,kicker,fontsize=16,weight='bold',color=WARN,va='top')
    fig.text(0.94,0.955,f'{page}/{N}',fontsize=16,color=MUTED,va='top',ha='right')
    fig.text(0.06,0.915,title,fontsize=40,weight='bold',color=ACCENT,va='top',linespacing=1.05)
    if text:fig.text(0.06,0.775,text,fontsize=20,color=INK,va='top',linespacing=1.3)
    if image is not None:
        ax=fig.add_axes(img_box);ax.imshow(image);ax.set_axis_off()
    if big:fig.text(0.06,0.165,big,fontsize=32,weight='bold',color=big_color,va='top',linespacing=1.15)
    fig.text(0.06,0.035,'github.com/kelian19/ml-climate-risk-catnat',fontsize=13,color=MUTED,va='bottom')
    if page<N:fig.text(0.94,0.035,'→',fontsize=30,color=ACCENT,va='bottom',ha='right',weight='bold')
    pdf.savefig(fig,facecolor=PAPER);plt.close(fig)

def main():
    e=json.loads((R/'ete_2026.json').read_text(encoding='utf-8'));h=e['headline_interval']
    oc=json.loads((R/'official_criterion.json').read_text(encoding='utf-8'));om=json.loads((R/'official_model.json').read_text(encoding='utf-8'))
    si=json.loads((R/'spatial_interp.json').read_text(encoding='utf-8'))['holdout_validation'];pr=oc['provisional_last_year'];c24=oc['check_2024_vs_report']['ours']
    gain=100*(1-si['KRIG']['rmse']/si['NN']['rmse']);auc=om['glm_officiel']['pooled']['auc'];lo,hi=round(h['low'],-1),round(h['high'],-1);exp_=round(e['expected_recognised_communes'],-2)
    out=FIG/'carrousel_catnat.pdf'
    with PdfPages(out) as pdf:
        # 1. Couverture
        fig=plt.figure(figsize=(10.8,13.5),dpi=100);fig.patch.set_facecolor(ACCENT)
        fig.text(0.07,0.90,'SÉCHERESSE CATNAT 2026',fontsize=18,weight='bold',color='#e8b9a8',va='top')
        fig.text(0.07,0.83,'Combien de communes\nseront reconnues en\ncatastrophe naturelle\nsécheresse en 2026 ?',fontsize=46,weight='bold',color='white',va='top',linespacing=1.08)
        fig.text(0.07,0.42,f'Peut-être {f(exp_)}.\nPeut-être {f(lo)}.\nPeut-être {f(hi)}.',fontsize=34,color='#cfe3c4',va='top',linespacing=1.3)
        fig.text(0.07,0.12,'Un modèle actuariel en 6 étapes,\ndes données Météo-France à un intervalle.',fontsize=20,color='white',va='top',linespacing=1.3)
        fig.text(0.93,0.035,'→',fontsize=34,color='white',va='bottom',ha='right',weight='bold');fig.text(0.07,0.035,f'1/{N}',fontsize=16,color='#cfe3c4',va='bottom')
        pdf.savefig(fig,facecolor=ACCENT);plt.close(fig)
        frame(pdf,2,'ÉTAPE 1 · LE BON INDICATEUR','Partir de l’indicateur\nofficiel',
              'Le SWI uniforme de Météo-France : l’humidité des sols\nque regarde le dispositif CatNat, sur 8 981 mailles\nde 8 km, chaque mois depuis 1959.',
              crop('pro_swi_etes_secs',(0.5,0.07,1.0,0.90)),'Anomalie d’été du SWI :\n2003, 2011, 2025, 2026',img_box=(0.10,0.20,0.80,0.46))
        frame(pdf,3,'ÉTAPE 2 · LE CRITÈRE OFFICIEL','Reproduire la règle,\nau chiffre près',
              f'Circulaire de 2024 : rang du SWI minimum sur 30 ans.\nAppliqué à 2024, mon calcul redonne le rapport\nMétéo-France : {c24["c1"]}, {c24["c2"]} et {c24["c1_or_c2"]} mailles.',
              crop('pro_critere_officiel',(0.0,0.10,0.64,0.92)),f'2026 : {f(pr["c1_cells"])} mailles sur 8 981\nau critère, après 9 mois',WARN,img_box=(0.04,0.21,0.92,0.44))
        frame(pdf,4,'ÉTAPE 3 · COMBLER LES TROUS','Estimer le SWI\nlà où il n’existe pas',
              'Le SWI n’existe que sur une grille de 8 km.\nLe krigeage l’estime au centre de chaque commune,\navec son incertitude.',
              side(crop('pro_interpolation_communes',(0.0,0.08,0.27,0.97)),crop('pro_interpolation_communes',(0.76,0.08,1.0,0.97))),
              f'−{gain:.0f} % d’erreur par rapport\nà la maille la plus proche',img_box=(0.04,0.21,0.92,0.47))
        frame(pdf,5,'ÉTAPE 4 · L’ARGILE','La sécheresse ne suffit pas :\nil faut de l’argile',
              'La carte BRGM des argiles gonflantes (121 399 polygones)\nsuperposée aux 34 746 communes : la part de chaque\ncommune en aléa moyen ou fort.',
              crop('pro_bivarie_argile_secheresse',(0.40,0.12,0.98,0.90)),'Rouge-brun : argile forte\net sécheresse sévère',img_box=(0.04,0.20,0.92,0.48))
        frame(pdf,6,'ÉTAPE 5 · LE MODÈLE','Prédire chaque commune,\nvalidé « en temps réel »',
              'Chaque année est prédite avec ce qu’on savait avant,\narrêtés non publiés exclus. Variables : critère officiel,\nargile, SWI krigé, historique publié.',
              crop('pro_nowcast_2026',(0.0,0.08,0.33,0.97)),f'AUC {f(auc,3)} sur 1995–2022',img_box=(0.10,0.20,0.80,0.48))
        frame(pdf,7,'ÉTAPE 6 · L’INTERVALLE','Un seul intervalle,\néprouvé sur le passé',
              f'Quatre méthodes comparées en temps réel ; retenue :\ncelle qui couvre bien sans s’élargir inutilement.\nElle aurait couvert {round(h["realtime_coverage"]*h["realtime_years"])} des {h["realtime_years"]} dernières années.',
              crop('pro_eventail_prediction',(0.0,0.08,1.0,0.68)),f'{f(lo)} – {f(hi)} communes\nà {100*h["level"]:.0f} %',img_box=(0.04,0.21,0.92,0.45))
        # 8. Conclusion
        fig=plt.figure(figsize=(10.8,13.5),dpi=100);fig.patch.set_facecolor(PAPER)
        fig.text(0.06,0.955,'CE QUE J’EN RETIENS',fontsize=16,weight='bold',color=WARN,va='top');fig.text(0.94,0.955,f'{N}/{N}',fontsize=16,color=MUTED,va='top',ha='right')
        fig.text(0.06,0.88,f'≈ {f(exp_)} communes\nattendues',fontsize=44,weight='bold',color=ACCENT,va='top',linespacing=1.05)
        fig.text(0.06,0.745,f'intervalle de prédiction à 90 % : {f(lo)} – {f(hi)}',fontsize=24,color=INK,va='top')
        fig.text(0.06,0.645,'Pourquoi si large ?',fontsize=30,weight='bold',color=INK,va='top')
        fig.text(0.06,0.59,'Le niveau annuel de reconnaissance varie\nbien plus que la météo ne l’explique.\nEt 2026 est plus sévère que toutes les années\nd’apprentissage : le modèle extrapole.',fontsize=21,color=MUTED,va='top',linespacing=1.35)
        fig.text(0.06,0.34,'Un intervalle étroit aurait été\nplus vendeur.',fontsize=34,weight='bold',color=INK,va='top',linespacing=1.1)
        fig.text(0.06,0.225,'Il aurait aussi été faux.',fontsize=34,weight='bold',color=WARN,va='top')
        fig.text(0.06,0.11,'Code, données publiques et note méthodologique :\ngithub.com/kelian19/ml-climate-risk-catnat',fontsize=18,color=ACCENT,va='top',linespacing=1.35)
        fig.text(0.06,0.035,'Partagez si c’était utile.',fontsize=14,color=MUTED,va='bottom')
        pdf.savefig(fig,facecolor=PAPER);plt.close(fig)
    print('écrit',out.name)

if __name__=='__main__':main()
