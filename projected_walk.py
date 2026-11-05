"""Opt-in manually calibrated front/back 2D projected stepping DRAFT.
Not reconstructed 3D, not unseen-sole generation, not a general high-quality gate.
"""
import math
import numpy as np
from PIL import Image
from joint_mesh import draw_mapped

def smooth(v):
 v=max(0,min(1,v));return v*v*(3-2*v)

def validate(rig):
 c=rig.get('projectedWalk')
 if c is None:return
 if not isinstance(c,dict) or c.get('confirmed') is not True:raise ValueError('Projected walk needs explicit calibration confirmation')
 if rig.get('view') not in ('front','back'):raise ValueError('Projected walk only supports front/back')
 if any(k in rig for k in ('walkProportions','walkGarment','hipAttachment','jointMeshes')):raise ValueError('Projected walk cannot combine side-specific meshes/materials')
 expected={'confirmed','hip','knee','ankle','shoulder','hand','armInner','armOuter','legScale','neutralHeight','ground','centerX','strideDepth','lift','depthProjection','shoeProjection'}
 if not expected<=set(c)<=expected|{'armFadeDepth','armAmplitude','armSpread','legInterpolation','rigidRegions'}:raise ValueError('Projected calibration fields mismatch')
 for k,v in c.items():
  if k not in ('confirmed','legInterpolation','rigidRegions') and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)):raise ValueError('Finite projected calibration required')
 if not 140<c['hip']<c['knee']<c['ankle']<340 or min(c['knee']-c['hip'],c['ankle']-c['knee'])<15:raise ValueError('Invalid leg source registration')
 if not 100<c['shoulder']<c['hand']<300 or not 120<c['armOuter']<c['armInner']<180:raise ValueError('Invalid arm source registration')
 if not 1<=c['legScale']<=1.4 or not 8<=c['strideDepth']<=48 or not 0<c['lift']<=18 or not .1<=c['depthProjection']<=.45 or not 0<=c['shoeProjection']<=.3:raise ValueError('Projected motion outside calibrated bounds')
 if c.get('legInterpolation','legacy-smooth') not in ('legacy-smooth','linear'):raise ValueError('Unknown projected leg interpolation')
 if not 0<=c.get('armAmplitude',6)<=10 or not 0<=c.get('armSpread',2)<=4:raise ValueError('Projected arm amplitude outside bounds')
 if 'armFadeDepth' in c and not 20<=c['armFadeDepth']<=40:raise ValueError('Arm fade depth must be20..40 source pixels')
 if (c['neutralHeight'],c['ground'],c['centerX'])!=(317,349,192):raise ValueError('This experimental projection requires normalized317 height /349 ground /192 center')
 regions=c.get('rigidRegions',[])
 if not isinstance(regions,list) or len(regions)>4:raise ValueError('Projected rigidRegions needs at most4 regions')
 def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
 for region in regions:
  if not isinstance(region,dict) or set(region)!={'box','feather'}:raise ValueError('Projected rigid region needs box/feather')
  box=region['box'];feather=region['feather']
  if not isinstance(box,list) or len(box)!=4 or not all(finite(v) for v in box):raise ValueError('Projected rigid box needs4 finite coordinates')
  x0,y0,x1,y1=box
  if not 0<=x0<x1<=384 or not 0<=y0<y1<=c['hip'] or min(x1-x0,y1-y0)<2:raise ValueError('Projected rigid region must be a nondegenerate torso box above hip')
  if not finite(feather) or not 4<=feather<=24:raise ValueError('Projected rigid region feather must be4..24 pixels')


def mapper_for(rig,t,neutral=False):
 c=rig['projectedWalk'];view=rig['view'];t=t%1;hip,knee,ankle=c['hip'],c['knee'],c['ankle'];gain=round(c['legScale']-1,12);rise=(ankle-hip)*gain;scale=317/(317+rise)
 def mapper(p):
  x,y=p;z=y
  # Same aesthetic leg ratio; neutral keeps head/torso shape and shoe size before height-fit; animated shoes are foreshortened below.
  z=y-rise+gain*max(0,min(y-hip,ankle-hip))
  if not neutral:
   bob=-.7*(1-math.cos(4*math.pi*t));z+=bob
   weights=[1-smooth((x-190)/4),smooth((x-190)/4)]
   for i,w in enumerate(weights):
    ph=(t+i*.5)%1
    if ph<.6:
     depth=c['strideDepth']/2-c['strideDepth']*ph/.6;lift=0
    else:
     q=(ph-.6)/.4;depth=-c['strideDepth']/2+c['strideDepth']*smooth(q);lift=c['lift']*math.sin(math.pi*q)**2
    # Sagittal two-link leg projected into front/back view, not planar outward IK.
    from motion import ik
    la=(knee-hip)*c['legScale'];lb=(ankle-knee)*c['legScale']
    ky,ay,err=ik([0,0],[depth,la+lb-3-lift],la,lb,-1)
    if err>1e-5:raise ValueError("Projected leg target is unreachable; reduce stride/lift or recalibrate source landmarks")
    projection=c['depthProjection']*(1 if view=='front' else -1)
    basehip=hip-rise+3
    targetk=basehip+ky[1]+projection*ky[0]
    targeta=basehip+ay[1]+projection*ay[0]
    pitch=1-c['shoeProjection']*math.sin(math.pi*max(0,min(1,(ph-.3)/.7)))**2
    targeta+=(1-pitch)*(349-ankle)
    oldk=knee-rise+gain*(knee-hip);olda=ankle
    if y<=knee:
     u=max(0,min(1,(y-hip)/(knee-hip)));amt=u if c.get('legInterpolation')=='linear' else smooth(u);delta=(targetk-oldk)*amt
    elif y<=ankle:
     u=max(0,min(1,(y-knee)/(ankle-knee)));amt=u if c.get('legInterpolation')=='linear' else smooth(u);delta=(targetk-oldk)*(1-amt)+(targeta-olda)*amt
    else:delta=targeta-olda+(y-ankle)*(pitch-1)
    z+=w*(delta-bob*smooth((y-hip)/(ankle-hip)))
    x+=w*(-1 if i==0 else 1)*.8*math.sin(2*math.pi*ph)*smooth((y-hip)/(ankle-hip))
   # Shoulder-led projected arm motion, opposite its leg. Only lateral sleeves/hands.
   if c['shoulder']<y<c['hand']+c.get('armFadeDepth',8):
    side=0 if p[0]<192 else 1;ph=(t+side*.5)%1;signal=math.cos(2*math.pi*ph)
    outer=smooth((abs(p[0]-192)-(192-c['armInner']))/12)
    along=smooth((y-c['shoulder'])/(c['hand']-c['shoulder']))
    if 'armFadeDepth' in c and y>c['hand']:along*=smooth((c['hand']+c['armFadeDepth']-y)/c['armFadeDepth'])
    z+=outer*along*c.get('armAmplitude',6)*signal*(-1 if view=='front' else 1)
    x+=outer*along*(1 if side else -1)*c.get('armSpread',2)*signal
  mapped=np.array([192+(x-192)*scale,349+(z-349)*scale])
  if not neutral and c.get('rigidRegions'):
   # Source-preserving torso accessories: a rigid core follows body bob only.
   # Smooth outer falloff retains a continuous surface; it is not hidden-art repair.
   weight=0.0
   for region in c['rigidRegions']:
    x0,y0,x1,y1=region['box']
    distance=max(x0-p[0],p[0]-x1,y0-p[1],p[1]-y1,0)
    weight=max(weight,1-smooth(distance/region['feather']))
   if weight:
    rigid=np.array([192+(p[0]-192)*scale,349+(p[1]-rise+bob-349)*scale])
    mapped=rigid if weight==1 else (1-weight)*mapped+weight*rigid
  return mapped
 return mapper

def source_image(rig,layers):
 src=Image.new('RGBA',(384,384));count=np.zeros((384,384),dtype=np.uint8)
 for name in rig['order']:
  layer=layers[name]
  if layer.getbbox() is None:raise ValueError('Projected part has no visible source pixels')
  if layer.size!=(384,384):raise ValueError('Projected layer must be384canvas')
  count+=np.asarray(layer.getchannel('A'))>0
  src.alpha_composite(layer)
 if count.max()>1:raise ValueError('Projected source layers must have exclusive pixel ownership; supply disjoint replacement layers')
 return src

def render(rig,layers,t,neutral=False):
 validate(rig);stats={};im=draw_mapped(source_image(rig,layers),mapper_for(rig,t,neutral),step=3,diagnostics=stats)
 return im,stats

def export(rig,layers,action,frames=None):
 from motion import require_ready
 require_ready(rig)
 if action!='walk':raise ValueError('Front/back projected dash has not been calibrated; choose walk')
 frames=8 if frames is None else frames
 if isinstance(frames,bool) or not isinstance(frames,int) or not 2<=frames<=120:raise ValueError('Invalid projected frame count')
 sheet=Image.new('RGBA',(384*6,384*math.ceil(frames/6)));records=[];stats=[];border=False
 for i in range(frames):
  im,d=render(rig,layers,i/frames);sheet.paste(im,((i%6)*384,(i//6)*384));stats.append(d)
  a=im.getchannel('A');border |= any(a.crop(b).getbbox() for b in ((0,0,384,1),(0,383,384,384),(0,0,1,384),(383,0,384,384)))
  records.append({'index':i,'rect':{'x':(i%6)*384,'y':(i//6)*384,'w':384,'h':384},'time':i/frames,'contacts':[s for j,s in enumerate(('left','right')) if (i/frames+j*.5)%1<.6]})
 return sheet,{'schema':'sprite-motion-lab/v0.1','status':'draft','view':rig['view'],'action':'walk','canvas':{'w':384,'h':384},'alpha':True,'duration':1,'fps':frames,'frames':records,'rootPivot':mapper_for(rig,0,True)(np.array(rig['root'],float)).tolist(),'sourceRootPivot':rig['root'],'projectedWalk':rig['projectedWalk'],'motionSpace':'2D projection of sagittal leg targets; image-space shoe compression; no physical world-contact proof','quality':{'approved':False,'borderAlpha':bool(border),'meshMaxActiveInvertedTriangles':max(d['activeInvertedTriangles'] for d in stats),'meshMinimumActiveAreaRatio':min(d['minimumActiveAreaRatio'] for d in stats)},'limitations':['Experimental front/back stepping, not side-level visual approval','Manual source registration and exclusive source-pixel ownership','Shoe vertical foreshortening is2D deformation; unseen sole is not generated','Contact labels are template states, not raster sole/world-slip certification']}
