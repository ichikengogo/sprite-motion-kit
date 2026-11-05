"""Confirmed walk-only proportions, source-coordinate retargeting and fixed display scale.
No automatic anatomy estimation, source repaint, per-frame bbox fitting or dash changes.
"""
import math
from copy import deepcopy
import numpy as np
from PIL import Image

def validate_proportions(rig):
 c=rig.get('walkProportions')
 if c is None:return
 if not isinstance(c,dict) or set(c)!={'confirmed','legScale','bodyRise','width','display'} or c['confirmed'] is not True:raise ValueError('Confirm walk proportions calibration')
 if rig.get('view')!='side' or rig.get('walkStyle')!='simple' or not rig.get('walkGarment'):raise ValueError('Proportions need registered side/simple garment walk')
 def finite(v):return isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v)
 if not finite(c['legScale']) or not 1<=c['legScale']<=1.5 or not finite(c['bodyRise']) or not 0<=c['bodyRise']<=60:raise ValueError('Invalid proportion length/rise')
 w=c['width'];d=c['display']
 if not isinstance(w,dict) or set(w)!={'amount','hemHold','ramp','endY','fade','kneeReduction','kneeRadius'} or not all(finite(v) for v in w.values()):raise ValueError('Invalid width profile')
 for k,lo,hi in [('amount',0,.2),('hemHold',0,8),('ramp',2,16),('fade',2,16),('kneeReduction',0,1),('kneeRadius',1,12)]:
  if not lo<=w[k]<=hi:raise ValueError('Width profile out of range: '+k)
 for side in ('left','right'):
  p=rig['parts'][side+'_shin'];start=rig['walkGarment']['panels'][side]['skinStart']
  if not start+w['hemHold']+w['ramp']<w['endY']<p['end'][1]:raise ValueError('Width band must stop before ankle')
  if rig['parts'][side+'_thigh']['start'][1]>=p['start'][1] or p['start'][1]>=p['end'][1]:raise ValueError('Proportions require downward registered leg axes')
 if not isinstance(d,dict) or set(d)!={'scale','anchor'} or not finite(d['scale']) or not .5<=d['scale']<=1.25 or not isinstance(d['anchor'],list) or len(d['anchor'])!=2 or not all(finite(v) and 0<=v<=384 for v in d['anchor']):raise ValueError('Invalid fixed display transform')

def active_rig(rig,action):
 out=dict(rig);out.pop('_activeWalkProportions',None)
 if action=='walk' and rig.get('walkProportions'):
  validate_proportions(rig);out['_activeWalkProportions']=True
 return out

def source_point(rig,side,p):
 f=rig['walkProportions']['legScale'];p=np.asarray(p,float);h=np.array(rig['parts'][side+'_thigh']['start']);k=np.array(rig['parts'][side+'_shin']['start']);a=np.array(rig['parts'][side+'_shin']['end']);u=np.clip((p[1]-h[1])/(k[1]-h[1]),0,1);v=np.clip((p[1]-k[1])/(a[1]-k[1]),0,1)
 return p+(f-1)*(u*(k-h)+v*(a-k))

def widen_source(rig,side,p):
 p=np.asarray(p,float);w=rig['walkProportions']['width'];start=rig['walkGarment']['panels'][side]['skinStart']
 def smooth(q):q=np.clip(q,0,1);return q*q*(3-2*q)
 weight=smooth((p[1]-start-w['hemHold'])/w['ramp'])*smooth((w['endY']-p[1])/w['fade']);knee=np.asarray(rig['parts'][side+'_shin']['start']);weight*=1-w['kneeReduction']*math.exp(-((p[1]-knee[1])/w['kneeRadius'])**2)
 part=rig['parts'][side+('_thigh' if p[1]<knee[1] else '_shin')];origin=np.array(part['start'],dtype=float);axis=np.array(part['end'],dtype=float)-origin;axis/=np.linalg.norm(axis);normal=np.array([-axis[1],axis[0]]);v=np.dot(p-origin,normal)
 return p+normal*v*w['amount']*weight

def retarget_pose(rig,transforms,diagnostics=None):
 from motion import ik,length,sub,angle
 validate_proportions(rig)
 c=rig['walkProportions'];f=c['legScale'];rise=c['bodyRise'];old=deepcopy(transforms);out={n:([p[0],p[1]-rise],a) for n,(p,a) in transforms.items()}
 for side in ('left','right'):
  h=np.array(out[side+'_thigh'][0]);target=np.array(old[side+'_foot'][0]);a=length(sub(rig['parts'][side+'_thigh']['end'],rig['parts'][side+'_thigh']['start']))*f;b=length(sub(rig['parts'][side+'_shin']['end'],rig['parts'][side+'_shin']['start']))*f;knee,ankle,clamp=ik(h,target,a,b,1 if rig.get('facing','right')=='left' else -1)
  if clamp>1e-5:raise ValueError('Proportion rise/length makes foot target unreachable: '+side)
  out[side+'_thigh']=(h.tolist(),angle(np.array(knee)-h));out[side+'_shin']=(knee,angle(np.array(ankle)-knee));out[side+'_foot']=(ankle,old[side+'_foot'][1])
  if diagnostics is not None:
   d=next(v for v in diagnostics if v['side']==side);d.update(hip=h.tolist(),knee=knee,ankle=ankle,lengths=[a,b],reach_error=clamp,proportionLegScale=f,proportionBodyRise=rise)
 return out

def display_point(rig,p):
 if not rig.get('_activeWalkProportions'):return np.asarray(p,float)
 d=rig['walkProportions']['display'];anchor=np.asarray(d['anchor']);return anchor+d['scale']*(np.asarray(p,float)-anchor)

def display_image(rig,image):
 if not rig.get('_activeWalkProportions'):return image
 d=rig['walkProportions']['display'];s=d['scale'];x,y=d['anchor'];return image.transform((384,384),Image.Transform.AFFINE,(1/s,0,x*(1-1/s),0,1/s,y*(1-1/s)),Image.Resampling.BICUBIC)
