"""Géostatistique du SWI uniforme : Moran, variogramme empirique et théorique, krigeage ordinaire, validation par blocs.

Les coordonnées sont les mètres Lambert-93 de la grille Météo-France (x93, y93). Toutes les fonctions sont
écrites en numpy/scipy pour rester testables sur des champs synthétiques à variogramme connu.
"""
import numpy as np
from scipy.optimize import curve_fit
from scipy.spatial import cKDTree

def knn_weights(xy,k=8):
    """Poids de voisinage (k plus proches voisins), standardisés par ligne ; renvoie (indices, poids)."""
    tree=cKDTree(xy);_,idx=tree.query(xy,k=k+1);idx=idx[:,1:]
    return idx,np.full(idx.shape,1./k)

def morans_i(z,idx,w,permutations=199,seed=0):
    """I de Moran avec p-valeur par permutations (hypothèse d'échangeabilité). Renvoie (I, E[I], p)."""
    z=np.asarray(z,float);d=z-z.mean();n=len(z)
    def stat(v):return n/np.sum(w)*np.sum(w*v[:,None]*v[idx])/np.sum(v*v)
    obs=stat(d);rng=np.random.default_rng(seed)
    sims=np.array([stat(rng.permutation(d)) for _ in range(permutations)])
    return float(obs),-1./(n-1),float((np.sum(sims>=obs)+1)/(permutations+1))

def empirical_variogram(xy,z,max_dist,bins=20,max_pairs=400000,seed=0):
    """Semi-variogramme empirique (Matheron) par classes de distance, sur un échantillon de paires."""
    z=np.asarray(z,float);n=len(z);rng=np.random.default_rng(seed)
    tree=cKDTree(xy);pairs=tree.query_pairs(max_dist,output_type='ndarray')
    if len(pairs)>max_pairs:pairs=pairs[rng.choice(len(pairs),max_pairs,replace=False)]
    h=np.linalg.norm(xy[pairs[:,0]]-xy[pairs[:,1]],axis=1);g=0.5*(z[pairs[:,0]]-z[pairs[:,1]])**2
    edges=np.linspace(0,max_dist,bins+1);k=np.digitize(h,edges)-1
    lag=np.array([h[k==b].mean() if np.any(k==b) else np.nan for b in range(bins)])
    gam=np.array([g[k==b].mean() if np.any(k==b) else np.nan for b in range(bins)])
    cnt=np.array([np.sum(k==b) for b in range(bins)])
    ok=cnt>30;return lag[ok],gam[ok],cnt[ok]

def spherical(h,nugget,psill,range_):
    h=np.asarray(h,float);r=np.minimum(h/range_,1.)
    return nugget+psill*(1.5*r-0.5*r**3)

def exponential(h,nugget,psill,range_):
    return nugget+psill*(1-np.exp(-3*np.asarray(h,float)/range_))

def gaussian(h,nugget,psill,range_):
    return nugget+psill*(1-np.exp(-3*(np.asarray(h,float)/range_)**2))

MODELS={'spherique':spherical,'exponentiel':exponential,'gaussien':gaussian}

def fit_variogram(lag,gam,counts,model='exponentiel'):
    """Ajustement pondéré par le nombre de paires (moindres carrés), paramètres positifs."""
    f=MODELS[model];sill=np.nanmax(gam);p0=[0.05*sill,0.9*sill,lag.max()/2]
    popt,_=curve_fit(f,lag,gam,p0=p0,sigma=1/np.sqrt(counts),bounds=([0,1e-12,1e-6],[np.inf,np.inf,np.inf]),maxfev=20000)
    resid=gam-f(lag,*popt);wrmse=float(np.sqrt(np.sum(counts*resid**2)/counts.sum()))
    return {'model':model,'nugget':float(popt[0]),'psill':float(popt[1]),'range':float(popt[2]),'wrmse':wrmse}

def kriging_weights(xy_obs,xy_new,params,n_neighbors=24):
    """Poids du krigeage ordinaire en voisinage glissant : (indices des voisins, poids, variance de krigeage).

    Les poids ne dépendent que de la géométrie et du variogramme, pas des valeurs : on les calcule une fois par point
    à estimer puis on les applique à n'importe quelle série (mois, années). Les poids somment à 1 (non-biais)."""
    f=MODELS[params['model']];args=(params['nugget'],params['psill'],params['range'])
    tree=cKDTree(xy_obs);k=min(n_neighbors,len(xy_obs));_,nn=tree.query(xy_new,k=k)
    nn=np.asarray(nn).reshape(len(xy_new),-1);W=np.zeros(nn.shape);var=np.zeros(len(xy_new))
    for i in range(len(xy_new)):
        pts=xy_obs[nn[i]];d=np.linalg.norm(pts[:,None]-pts[None],axis=2);g=f(d,*args);np.fill_diagonal(g,0.)
        n=len(pts);A=np.ones((n+1,n+1));A[:n,:n]=g;A[n,n]=0.
        b=np.ones(n+1);b[:n]=f(np.linalg.norm(pts-xy_new[i],axis=1),*args)
        sol=np.linalg.lstsq(A,b,rcond=None)[0];W[i]=sol[:n];var[i]=float(sol@b)
    return nn,W,np.maximum(var,0.)

def apply_weights(values,nn,W):
    """Applique les poids à des valeurs observées (dernier axe = points d'observation) ; valeurs manquantes propagées."""
    return np.einsum('...ik,ik->...i',np.asarray(values)[...,nn],W)

def ordinary_kriging(xy_obs,z_obs,xy_new,params,n_neighbors=24):
    """Krigeage ordinaire en voisinage glissant ; renvoie (prédiction, variance de krigeage)."""
    nn,W,var=kriging_weights(xy_obs,xy_new,params,n_neighbors)
    return np.einsum('ik,ik->i',W,np.asarray(z_obs)[nn]),var

def block_cv_kriging(xy,z,params,block_km=100.,n_neighbors=24,max_blocks=12,seed=0):
    """Validation par blocs spatiaux : on retire un disque de rayon `block_km` autour de points de test et on
    krige ce disque avec le reste (aucune voisine immédiate). Renvoie RMSE et couverture de l'intervalle ±1,96σ."""
    rng=np.random.default_rng(seed);centers=xy[rng.choice(len(xy),min(max_blocks,len(xy)),replace=False)]
    err=[];cover=[];zs=[]
    for c in centers:
        d=np.linalg.norm(xy-c,axis=1);test=np.where(d<block_km*1000.)[0];train=np.where(d>=block_km*1000.)[0]
        if len(test)<5 or len(train)<50:continue
        sel=test[rng.choice(len(test),min(60,len(test)),replace=False)]
        p,v=ordinary_kriging(xy[train],z[train],xy[sel],params,n_neighbors)
        e=z[sel]-p;err.append(e);sd=np.sqrt(np.maximum(v,1e-12));cover.append(np.abs(e)<=1.96*sd);zs.append(e/sd)
    e=np.concatenate(err);cv=np.concatenate(cover);zz=np.concatenate(zs)
    return {'rmse':float(np.sqrt(np.mean(e**2))),'mae':float(np.mean(np.abs(e))),'coverage_95':float(cv.mean()),'std_standardized_error':float(zz.std()),'n':int(len(e))}
