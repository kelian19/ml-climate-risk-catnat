"""Mesures probabilistes et calibration « portefeuille » (nombre attendu de communes reconnues)."""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

EPS=1e-6

def log_loss(y,p):
    p=np.clip(p,EPS,1-EPS);return float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p)))

def brier(y,p):return float(np.mean((p-y)**2))

def scores(y,p,reference=None):
    """Log-loss, Brier, AUC ; score de compétence = 1 − perte/perte de référence (0 : pas mieux que la référence)."""
    y=np.asarray(y);p=np.asarray(p)
    out={'log_loss':log_loss(y,p),'brier':brier(y,p),'auc':float(roc_auc_score(y,p)) if 0<y.sum()<len(y) else float('nan'),
         'observed':int(y.sum()),'expected':float(p.sum())}
    if reference is not None:
        out['log_loss_skill']=1-out['log_loss']/log_loss(y,reference);out['brier_skill']=1-out['brier']/brier(y,reference)
    return out

def by_year(pred,col):
    """Observé contre attendu par année : la calibration agrégée est ce qui compte pour une charge de portefeuille."""
    g=pred.groupby('year').agg(observed=('y','sum'),expected=(col,'sum'),communes=('y','size'))
    g['ratio_obs_exp']=g.observed/g.expected
    return g.reset_index()

def calibration_table(y,p,bins=10):
    """Fréquence observée contre prédite par décile de probabilité prédite."""
    d=pd.DataFrame({'y':y,'p':p});d['bin']=pd.qcut(d.p.rank(method='first'),bins,labels=False)
    return d.groupby('bin').agg(p_mean=('p','mean'),y_rate=('y','mean'),n=('y','size')).reset_index()
