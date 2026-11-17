"""Cartes et visualisations avancées (communes, départements, régions, grilles Safran, krigeage, bivarié)."""
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap,ListedColormap,Normalize,LogNorm,TwoSlopeNorm,to_rgb
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib import patheffects as pe

INK='#1c2b27';MUTED='#6a7a72';PAPER='#fbfaf6';ACCENT='#174f43';WARN='#b24a3a'
REG_NAMES={'11':'Île-de-France','24':'Centre-Val de Loire','27':'Bourgogne-Franche-Comté','28':'Normandie','32':'Hauts-de-France','44':'Grand Est','52':'Pays de la Loire','53':'Bretagne','75':'Nouvelle-Aquitaine','76':'Occitanie','84':'Auvergne-Rhône-Alpes','93':"Provence-Alpes-Côte d'Azur",'94':'Corse'}
DRY=LinearSegmentedColormap.from_list('dry',['#f6f1e4','#f2d58a','#e8a43c','#cf6a1f','#a3361b','#5b1a14'])
WET_DRY=LinearSegmentedColormap.from_list('wetdry',['#07566b','#3a9ab0','#bfe3e8','#f7f4ea','#f0cf8e','#d98a2b','#8c2d12'])
SEQ_GREEN=LinearSegmentedColormap.from_list('green',['#f4f7ef','#c5dcb0','#7fb77e','#3d8a63','#175b4a','#0b2f2a'])

def setup():
    plt.rcParams.update({'figure.facecolor':PAPER,'axes.facecolor':PAPER,'savefig.facecolor':PAPER,'font.family':'DejaVu Sans','text.color':INK,'axes.labelcolor':INK,
        'xtick.color':MUTED,'ytick.color':MUTED,'axes.edgecolor':MUTED,'axes.titleweight':'bold','axes.titlesize':11,'font.size':9})

def base_layers(raw):
    """Communes (Lambert-93), départements et régions fusionnés, noms des communes."""
    com=gpd.read_file(f'/vsigzip/{raw}/communes-100m.geojson.gz');com=com[~com.code.str.startswith(('97','98'))][['code','nom','departement','region','geometry']].to_crs(2154)
    com['geometry']=com.geometry.make_valid()
    dep=com.dissolve(by='departement',as_index=False)[['departement','region','geometry']];reg=com.dissolve(by='region',as_index=False)[['region','geometry']]
    return com,dep,reg

def finish_map(ax,dep=None,reg=None,dep_lw=0.25,reg_lw=0.9):
    if dep is not None:dep.boundary.plot(ax=ax,color='white',linewidth=dep_lw,alpha=.8,zorder=3)
    if reg is not None:reg.boundary.plot(ax=ax,color=INK,linewidth=reg_lw,alpha=.75,zorder=4)
    ax.set_axis_off();ax.set_aspect('equal')

def label_regions(ax,reg,size=7):
    for r in reg.itertuples():
        c=r.geometry.representative_point();ax.text(c.x,c.y,REG_NAMES.get(r.region,r.region).replace('-','-\n',1) if len(REG_NAMES.get(r.region,''))>14 else REG_NAMES.get(r.region,r.region),
            ha='center',va='center',fontsize=size,color=INK,weight='bold',path_effects=[pe.withStroke(linewidth=2.2,foreground='white',alpha=.85)],zorder=6)

def scale_bar(ax,length_km=200,loc=(0.06,0.04)):
    x0,x1=ax.get_xlim();y0,y1=ax.get_ylim();x=x0+loc[0]*(x1-x0);y=y0+loc[1]*(y1-y0)
    ax.plot([x,x+length_km*1000],[y,y],color=INK,lw=2.2,solid_capstyle='butt',zorder=7);ax.text(x+length_km*500,y+(y1-y0)*0.012,f'{length_km} km',ha='center',va='bottom',fontsize=7,color=INK,zorder=7)

def north_arrow(ax,loc=(0.93,0.9)):
    x0,x1=ax.get_xlim();y0,y1=ax.get_ylim();x=x0+loc[0]*(x1-x0);y=y0+loc[1]*(y1-y0);h=(y1-y0)*0.06
    ax.annotate('',xy=(x,y+h),xytext=(x,y),arrowprops=dict(arrowstyle='-|>',color=INK,lw=1.4),zorder=7);ax.text(x,y+h*1.15,'N',ha='center',va='bottom',fontsize=8,weight='bold',color=INK)

def title_block(fig,title,subtitle,source,y=0.985):
    fig.text(0.02,y,title,ha='left',va='top',fontsize=17,weight='bold',color=ACCENT);fig.text(0.02,y-0.032,subtitle,ha='left',va='top',fontsize=9.5,color=MUTED)
    fig.text(0.02,0.012,source,ha='left',va='bottom',fontsize=7,color=MUTED)

def hbar_colorbar(fig,ax,cmap,norm,label,width=0.6,pad=0.02,ticks=None,fmt=None):
    cax=ax.inset_axes([(1-width)/2,-0.045-pad,width,0.018]);cb=fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,orientation='horizontal',ticks=ticks)
    cb.outline.set_linewidth(0.4);cb.ax.tick_params(labelsize=7,length=2);cb.set_label(label,fontsize=8,color=INK,labelpad=2)
    if fmt:cb.ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt))
    return cb

# --------------------------------------------------------------------- carte bivariée 3×3
BIV=np.array([[['#e8e8e8','#cddbe9','#a5c5de'],['#e3d0d9','#c7b8cf','#9a9ec0'],['#d9a9bd','#be90ab','#8a6f9c']],
              [['#e8e8e8','#ece1c1','#f0d98a'],['#eab9a7','#d9a384','#c98a52'],['#e08a6e','#c96a4a','#a7421f']]],dtype=object)

def bivariate_colors(x,y,qx,qy,scheme=1):
    """Couleur d'une carte bivariée 3×3 par terciles (bornes qx, qy de longueur 2) ; renvoie des couleurs hex et les indices."""
    ix=np.digitize(x,qx);iy=np.digitize(y,qy);grid=BIV[scheme]
    return np.array([grid[j][i] for i,j in zip(ix,iy)],dtype=object),ix,iy

def bivariate_legend(ax,xlabel,ylabel,scheme=1):
    for i in range(3):
        for j in range(3):ax.add_patch(plt.Rectangle((i,j),1,1,color=BIV[scheme][j][i],ec='white',lw=1))
    ax.set_xlim(0,3);ax.set_ylim(0,3);ax.set_xticks([]);ax.set_yticks([]);ax.set_xlabel(xlabel+'  →',fontsize=7);ax.set_ylabel(ylabel+'  →',fontsize=7)
    for s in ax.spines.values():s.set_visible(False)
    ax.set_aspect('equal')
