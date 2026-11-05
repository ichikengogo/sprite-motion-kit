"""Confirmed walk-only waist and two cloth tubes; no generated pixels or gait edits.
Hem quads use the exact source-point skinning mapper used by the legs.
"""
import math
import numpy as np
from PIL import Image
from joint_mesh import joint_mapper,draw_mapped
SIZE=(384,384)
def validate_garment(rig):
 c=rig.get('walkGarment')
 if c is None:return
 if not isinstance(c,dict) or set(c)-{'mode','confirmed','panels','waistBottom','waistFeather','hemConnection','waistLowerEdge','waistConnection','sourceHemMode'} or not {'mode','confirmed','panels','waistBottom','waistFeather'}<=set(c) or c.get('mode')!='waist-and-tubes' or c.get('confirmed') is not True:raise ValueError('Confirm authored walk garment first')
 if rig.get('view')!='side' or rig.get('walkStyle')!='simple' or not rig.get('hipAttachment'):raise ValueError('Garment needs side simple split-cloth walk')
 if 'sourceHemMode' in c and (c['sourceHemMode'] not in ('registered-width','preserve-x') or not c.get('hemConnection')):raise ValueError('sourceHemMode requires skin-mesh hem connection and registered-width/preserve-x')
 if not isinstance(c['panels'],dict) or set(c['panels'])!={'left','right'}:raise ValueError('Both garment tubes required')
 def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
 if not all(finite(c[k]) for k in ('waistBottom','waistFeather')) or not 1<=c['waistFeather']<=8:raise ValueError('Invalid waist fade')
 for side,p in c['panels'].items():
  if not isinstance(p,dict) or set(p)!={'sourceBox','hemX','skinStart'}:raise ValueError('Invalid garment panel')
  b=p['sourceBox'];h=p['hemX']
  if not isinstance(b,list) or len(b)!=4 or not all(isinstance(v,int) and not isinstance(v,bool) for v in b):raise ValueError('Garment sourceBox needs integer bounds')
  x0,y0,x1,y1=b
  if not 0<=x0<x1<=384 or not 0<=y0<y1<=384 or x1-x0>80 or y1-y0>70:raise ValueError('Garment sourceBox out of range')
  if p['skinStart']!=y1 or not isinstance(p['skinStart'],int) or isinstance(p['skinStart'],bool):raise ValueError('Skin boundary must equal panel lower row')
  if not isinstance(h,list) or len(h)!=2 or not all(finite(v) for v in h) or not x0<=h[0]<h[1]<=x1 or h[1]-h[0]<8:raise ValueError('Invalid garment hem registration')
  if not y0+c['waistFeather']<c['waistBottom']<y1:raise ValueError('Waist must end within garment')
  edge=c.get('waistLowerEdge')
  if edge is not None:
   if not isinstance(edge,list) or not 2<=len(edge)<=8 or any(not isinstance(v,list) or len(v)!=2 or not all(finite(n) for n in v) for v in edge):raise ValueError('Invalid waist lower profile')
   if any(not 0<=x<=384 or not y0+c['waistFeather']<y<y1 for x,y in edge) or any(edge[i][0]>=edge[i+1][0] for i in range(len(edge)-1)):raise ValueError('Waist profile out of range')
  wc=c.get('waistConnection')
  if wc is not None:
   if not isinstance(wc,dict) or set(wc)!={'mode','topLift','depth','sourceFrontX','fadeX'} or wc['mode']!='front-tube' or not all(finite(wc[k]) for k in ('topLift','depth','sourceFrontX','fadeX')):raise ValueError('Invalid waist connection')
   if not 0<=wc['topLift']<=4 or not 8<=wc['depth']<=28 or not 0<=wc['sourceFrontX']<wc['fadeX']<=384 or not 8<=wc['fadeX']-wc['sourceFrontX']<=60 or not c.get('hemConnection'):raise ValueError('Waist connection out of range')

  conn=c.get('hemConnection')
  if conn is not None and (not isinstance(conn,dict) or set(conn)!={'mode','overlap'} or conn['mode']!='skin-mesh' or not finite(conn['overlap']) or not 0<=conn['overlap']<=3):raise ValueError('Invalid hem connection')
  name=side+'_thigh';child=side+'_shin';m=next((m for m in rig.get('jointMeshes',[]) if m['parent']==name),None)
  if m is None or m.get('walkContour')!='centerline':raise ValueError('Garment needs centerline thigh mesh')
  if not y0<=rig['parts'][name]['start'][1]<y1<=rig['parts'][child]['start'][1]:raise ValueError('Garment must stay between waist and knee')

def panel_hem_x(config,panel,x):
 """Source-cutout option keeps each hem sample at its original x."""
 if config.get('sourceHemMode')=='preserve-x':return x
 x0,_,x1,_=panel['sourceBox'];u=(x-x0)/(x1-x0)
 return panel['hemX'][0]+u*(panel['hemX'][1]-panel['hemX'][0])

def apply_garment(rig,layers,transforms,diagnostics=None):
 cfg=rig['walkGarment'];out=Image.new('RGBA',SIZE);layers=dict(layers)
 rig['_garmentMeshBounds']={}
 def material(name):
  im=layers.get('walk:garment_'+name)
  if not isinstance(im,Image.Image) or im.mode!='RGBA' or im.size!=SIZE or im.getbbox() is None:raise ValueError('Missing garment material: '+name)
  return im
 def torso_point(p):
  part=rig['parts']['torso'];dst,theta=transforms['torso'];a=theta-math.atan2(part['end'][1]-part['start'][1],part['end'][0]-part['start'][0]);c=math.cos(a);s=math.sin(a)
  p=np.array(p,float);wc=cfg.get('waistConnection');top=min(v['sourceBox'][1] for v in cfg['panels'].values())
  if wc:p[1]-=wc['topLift']*max(0,min(1,(top+wc['depth']-p[1])/wc['depth']))
  return np.array(dst)+np.array([[c,-s],[s,c]])@(p-part['start'])
 for side in ('left','right'):
  p=cfg['panels'][side]
  x0,y0,x1,y1=p['sourceBox'];name=side+'_thigh';m=next(m for m in rig['jointMeshes'] if m['parent']==name)
  mapper=joint_mapper(rig,transforms,name,m['child'],m.get('radius',10),m['walkContour'],m.get('walkAnkleDepth',0),m.get('walkClothWidth'),m.get('walkAnkleOffsetX',0),cuff_normal=m.get('walkCuffNormal'))
  src=np.array([[x0,y0],[x1,y0],[x1,y1],[x0,y1]],float);dst=np.array([torso_point(src[0]),torso_point(src[1]),mapper(np.array([x1 if cfg.get('sourceHemMode')=='preserve-x' else p['hemX'][1],y1],float)),mapper(np.array([x0 if cfg.get('sourceHemMode')=='preserve-x' else p['hemX'][0],y1],float))])
  edges=np.roll(dst,-1,axis=0)-dst;nxt=np.roll(edges,-1,axis=0);cross=edges[:,0]*nxt[:,1]-edges[:,1]*nxt[:,0];area=.5*abs(np.sum(dst[:,0]*np.roll(dst[:,1],-1)-dst[:,1]*np.roll(dst[:,0],-1)));ratio=area/((x1-x0)*(y1-y0))
  # A sparse original cutout can have empty source-box corners outside its cuff.
  # Its opt-in mesh path is checked using occupied triangles below, not the
  # enclosing quad; legacy rectangular panels retain their exact early guard.
  source_cutout=cfg.get('sourceHemMode')=='preserve-x' and bool(cfg.get('hemConnection'))
  if not np.isfinite(dst).all() or (not source_cutout and (min(cross)<=1e-5 or ratio<.08)):raise ValueError('Garment panel folds/collapses: '+side)
  if diagnostics is not None:diagnostics.append({'side':'garment_'+side,'areaRatio':float(ratio),'sourceQuad':src.tolist(),'destinationQuad':dst.tolist()})
  image=material(side);a=np.asarray(image);mask=np.zeros(SIZE,dtype=np.uint8);mask[y0:y1,x0:x1]=255
  if not np.any(a[:,:,3]&mask):raise ValueError('Empty garment source box')
  clipped=image.copy();clipped.putalpha(Image.fromarray(np.minimum(a[:,:,3],mask)))
  A=[];b=[]
  for (x,y),(u,v) in zip(dst,src):A.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);b.extend([u,v])
  connection=cfg.get('hemConnection')
  if connection:
   def cloth_map(v):
    x,y=v;t=(y-y0)/(y1-y0);hx=panel_hem_x(cfg,p,x)
    return (1-t)*torso_point([x,y0])+t*mapper(np.array([hx,y1+connection['overlap']],float))
   stats={};cloth=draw_mapped(clipped,cloth_map,step=2,diagnostics=stats,grid_bounds=(x0,y0,x1,y1))
   if stats['activeInvertedTriangles'] or stats['minimumActiveAreaRatio']<.08:raise ValueError('Mapped garment folds/collapses: '+side)
   if diagnostics is not None:diagnostics.append({'side':'garment_mesh_'+side,'areaRatio':stats['minimumActiveAreaRatio'],'activeInvertedTriangles':stats['activeInvertedTriangles']})
   out.alpha_composite(cloth)
  else:out.alpha_composite(clipped.transform(SIZE,Image.Transform.PERSPECTIVE,np.linalg.solve(np.array(A),b),Image.Resampling.BICUBIC))
  # Keep the original mesh grid while removing cloth pixels; no incidental leg retessellation.
  combined=layers[name].copy();combined.alpha_composite(layers[m['child']]);rig['_garmentMeshBounds'][name]=combined.getbbox()
  leg=layers[name].copy();alpha=np.array(leg.getchannel('A'));alpha[:p['skinStart']]=0;leg.putalpha(Image.fromarray(alpha));layers[name]=leg
 waist=material('waist').copy();box=waist.getbbox();boxes=[p['sourceBox'] for p in cfg['panels'].values()]
 if box[0]<min(b[0] for b in boxes)-8 or box[2]>max(b[2] for b in boxes)+8 or box[1]<min(b[1] for b in boxes) or box[3]>max(b[3] for b in boxes):raise ValueError('Waist material extends outside garment region')
 a=np.array(waist);yy=np.arange(384)[:,None];edge=cfg.get('waistLowerEdge');bottom=np.interp(np.arange(384),[p[0] for p in edge],[p[1] for p in edge])[None,:] if edge else cfg['waistBottom'];a[:,:,3]=(a[:,:,3]*np.clip((bottom-yy)/cfg['waistFeather'],0,1)).astype('uint8');waist=Image.fromarray(a)
 if waist.getbbox() is None:raise ValueError('Waist fade removes all material')
 part=rig['parts']['torso'];dest,theta=transforms['torso'];angle=theta-math.atan2(part['end'][1]-part['start'][1],part['end'][0]-part['start'][0]);c=math.cos(angle);s=math.sin(angle);tx=part['start'][0]-c*dest[0]-s*dest[1];ty=part['start'][1]+s*dest[0]-c*dest[1]
 
 if cfg.get('waistConnection'):
  wc=cfg['waistConnection'];fp=cfg['panels']['left'];fx0,fy0,fx1,fy1=fp['sourceBox'];fm=next(m for m in rig['jointMeshes'] if m['parent']=='left_thigh');fmapper=joint_mapper(rig,transforms,'left_thigh',fm['child'],fm['radius'],fm['walkContour'],fm.get('walkAnkleDepth',0),fm.get('walkClothWidth'),fm.get('walkAnkleOffsetX',0),cuff_normal=fm.get('walkCuffNormal'))
  def frontmap(v):
   x,y=v;t=(y-fy0)/(fy1-fy0);target=(1-t)*torso_point([fx0,fy0])+t*fmapper(np.array([fx0 if cfg.get('sourceHemMode')=='preserve-x' else fp['hemX'][0],fy1+cfg['hemConnection']['overlap']],float));base=torso_point([wc['sourceFrontX'],y]);q=max(0,min(1,(y-fy0)/wc['depth']));q=q*q*(3-2*q);w=max(0,min(1,(wc['fadeX']-x)/(wc['fadeX']-wc['sourceFrontX'])));return torso_point(v)+q*w*(target-base)
  stats={};waist=draw_mapped(waist,frontmap,step=2,diagnostics=stats)
  if stats['activeInvertedTriangles'] or stats['minimumActiveAreaRatio']<.08:raise ValueError('Waist connection folds/collapses')
  if diagnostics is not None:diagnostics.append({'side':'garment_waist','areaRatio':stats['minimumActiveAreaRatio'],'activeInvertedTriangles':stats['activeInvertedTriangles']})
  out.alpha_composite(waist)
 else:out.alpha_composite(waist.transform(SIZE,Image.Transform.AFFINE,(c,s,tx,-s,c,ty),Image.Resampling.BICUBIC))
 layers['pelvis']=out
 return layers
