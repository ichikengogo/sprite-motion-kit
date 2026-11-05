import unittest,copy
from PIL import Image,ImageDraw
import test_garment
from motion import validate,render,export,pose
from hip_cloth import prepare
from seam_quality import measure_seams
class GarmentSeamTests(unittest.TestCase):
 def fixture(self):
  r,l=test_garment.GarmentTests().fixture();r['motionScale']=.1
  for side,p in r['walkGarment']['panels'].items():
   x0,y0,x1,y1=p['sourceBox'];im=Image.new('RGBA',(384,384));ImageDraw.Draw(im).rectangle((x0,y0,x1-1,y1-2),fill=(65,55,45,255));l['walk:garment_'+side]=im;p['hemX']=[x0,x1]
   skin=Image.new('RGBA',(384,384));ImageDraw.Draw(skin).rectangle((x0+5,y0,x1-6,int(r['parts'][side+'_shin']['start'][1])+4),fill=(240,190,150,255));l[side+'_thigh']=skin;l['walk:'+side+'_thigh']=skin.copy()
  return r,l
 def test_mapped_allowance_closes_painted_edge_gap(self):
  import numpy as np
  from joint_mesh import draw_mapped
  im=Image.new('RGBA',(384,384));ImageDraw.Draw(im).rectangle((100,100,119,118),fill=(65,55,45,255));before=im.tobytes()
  old=draw_mapped(im,lambda p:p,step=2,grid_bounds=(100,100,120,120))
  new=draw_mapped(im,lambda p:np.array([p[0],100+(p[1]-100)*22/20]),step=2,grid_bounds=(100,100,120,120))
  self.assertEqual(old.getpixel((110,119))[3],0);self.assertGreaterEqual(new.getpixel((110,119))[3],240);self.assertEqual(new.getpixel((110,119))[:3],(65,55,45));self.assertEqual(im.tobytes(),before)
 def test_internal_not_external_alpha_diagnostic(self):
  import math
  r,l=self.fixture();t={n:(p['start'],math.atan2(p['end'][1]-p['start'][1],p['end'][0]-p['start'][0])) for n,p in r['parts'].items()};rr,ll,tt=prepare(r,l,t)
  empty=measure_seams(rr,ll,tt,Image.new('RGBA',(384,384)))
  solid=measure_seams(rr,ll,tt,Image.new('RGBA',(384,384),(65,55,45,255)))
  self.assertTrue(empty);self.assertTrue(all(v['alpha']==0 for v in empty));self.assertTrue(all(v['alpha']==255 for v in solid))
  _,meta=export(r,l,'walk');self.assertIn('garmentInternalSeamWarning',meta['quality'])
 def test_unresolved_registration_remains_warning(self):
  # A confirmed but poorly matched synthetic cloth is intentionally retained:
  # underlap is not a universal guarantee, and its real gaps must stay visible in QA.
  r,l=self.fixture();r['walkGarment']['hemConnection']={'mode':'skin-mesh','overlap':2};_,meta=export(r,l,'walk')
  self.assertLess(meta['quality']['garmentInternalSeamMinAlpha'],220);self.assertTrue(meta['quality']['garmentInternalSeamWarning'])
 def test_bad_connection_profile_and_no_pose_change(self):
  r,l=self.fixture();original=copy.deepcopy(r)
  for c in [{'mode':'skin-mesh','overlap':float('nan')},{'mode':'skin-mesh','overlap':4},{'mode':'fill','overlap':2}]:
   r['walkGarment']['hemConnection']=c
   with self.assertRaises(ValueError):validate(r)
  r['walkGarment']['hemConnection']={'mode':'skin-mesh','overlap':2};r['walkGarment']['waistLowerEdge']=[[200,240],[100,240]]
  with self.assertRaises(ValueError):validate(r)
  del r['walkGarment']['waistLowerEdge'];self.assertEqual(pose(r,'walk',.25),pose(original,'walk',.25));self.assertEqual(render(r,l,'dash',0)[0].tobytes(),render(original,l,'dash',0)[0].tobytes())
