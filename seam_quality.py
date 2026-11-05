"""Raster coverage at confirmed internal cloth/skin boundaries, not outer AA edges.
This is a diagnostic, not a substitute for multi-background visual review.
"""
import numpy as np
from joint_mesh import joint_mapper
from proportions import display_point

def measure_seams(rig,layers,transforms,image):
 rows=[];pixels=np.asarray(image)
 for side in ('left','right'):
  name=side+'_thigh';m=next(m for m in rig['jointMeshes'] if m['parent']==name);mapper=joint_mapper(rig,transforms,name,m['child'],m.get('radius',10),m['walkContour'],m.get('walkAnkleDepth',0),m.get('walkClothWidth'),m.get('walkAnkleOffsetX',0),cuff_normal=m.get('walkCuffNormal'));cut=rig['walkGarment']['panels'][side]['skinStart'];xs=np.where(np.asarray(layers[name])[cut,:,3]>200)[0]
  # Trim endpoints so intentional outside silhouettes do not masquerade as seam holes.
  for x in xs[2:-2]:
   px,py=np.rint(display_point(rig,mapper(np.array([x,cut],float)))).astype(int)
   alpha=int(pixels[py,px,3]) if 0<=px<384 and 0<=py<384 else 0
   rows.append({'side':side,'source':[int(x),cut],'pixel':[int(px),int(py)],'alpha':alpha})
 rows.extend(measure_upper_seam(rig,layers,transforms,image))
 return rows


def measure_upper_seam(rig,layers,transforms,image):
 """Sample just below the actual torso silhouette across the registered front waist.
 Includes a source gap up to panel top; exterior sides and unrelated limbs excluded.
 Still requires visual inspection of the cap/tube outer contour.
 """
 import math
 cfg=rig['walkGarment'];boxes=[p['sourceBox'] for p in cfg['panels'].values()];top=min(b[1] for b in boxes);left=min(b[0] for b in boxes)
 wc=cfg.get('waistConnection',{});right=min(max(b[2] for b in boxes),int(wc.get('fadeX',left+24)))
 src=np.asarray(layers['torso']);pixels=np.asarray(image);p=rig['parts']['torso'];dest,theta=transforms['torso'];a=theta-math.atan2(p['end'][1]-p['start'][1],p['end'][0]-p['start'][0]);rot=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]]);rows=[]
 for x in range(left,right):
  ys=np.where(src[:,x,3]>200)[0]
  if not len(ys):continue
  y=int(ys[-1])
  if not top-12<=y<=top+12:continue
  for yy in range(y+1,max(y+2,top+1)):
   px,py=np.rint(display_point(rig,np.array(dest)+rot@(np.array([x,yy])-p['start']))).astype(int);alpha=int(pixels[py,px,3]) if 0<=px<384 and 0<=py<384 else 0
   rows.append({'side':'upper-waist','source':[x,yy],'pixel':[int(px),int(py)],'alpha':alpha})
 return rows
