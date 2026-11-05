import copy,hashlib,unittest
import test_garment
from garment import panel_hem_x
from motion import render,validate,pose

class SourceHemMappingTests(unittest.TestCase):
 def fixture(self):
  r,l=test_garment.GarmentTests().fixture()
  r['walkGarment']['hemConnection']={'mode':'skin-mesh','overlap':1}
  return r,l
 def test_preserve_source_x_not_box_to_hem_compression(self):
  panel={'sourceBox':[150,239,191,275],'hemX':[164,187],'skinStart':275}
  cfg={'sourceHemMode':'preserve-x'}
  for x in (150,157.5,164,175,187,191):self.assertEqual(panel_hem_x(cfg,panel,x),x)
  self.assertEqual(panel_hem_x({},panel,150),164)
  self.assertEqual(panel_hem_x({},panel,191),187)
  self.assertNotEqual(panel_hem_x({},panel,164),164)
 def test_legacy_raster_bytes_unchanged(self):
  # Captured from actual renderer immediately before adding the option.
  expected=['496a4f4b762e7780aeaba9489fab05222e11607cb62ae329339602fe7ac91f2f','72c56fc6c741f6dbf69870ee48aadebef3513e1a2d05e01f29ffde45222e2faa','0329b8aa5c6db16f767f91c224205b841b0c836c4a61c00c7679f3d3f6c08db0','9c4055906b3106d614a789f110a17af469d3faf1578f15b8780a080b27ac2940']
  r,l=self.fixture()
  for phase,h in zip((0,.25,.5,.75),expected):self.assertEqual(hashlib.sha256(render(r,l,'walk',phase)[0].tobytes()).hexdigest(),h)
 def test_optin_no_pose_material_or_dash_mutation(self):
  r,l=self.fixture();old=copy.deepcopy(r);saved={n:im.tobytes() for n,im in l.items()}
  r['walkGarment']['sourceHemMode']='preserve-x';validate(r);confirmed=copy.deepcopy(r)
  for t in (0,.25,.5,.75):
   self.assertEqual(pose(r,'walk',t),pose(old,'walk',t));render(r,l,'walk',t)
  self.assertEqual(r,confirmed);self.assertEqual(saved,{n:im.tobytes() for n,im in l.items()})
  self.assertEqual(render(r,l,'dash',0)[0].tobytes(),render(old,l,'dash',0)[0].tobytes())
 def test_bad_mode_or_missing_connection_rejected(self):
  r,l=self.fixture()
  for value in (True,None,'guess',''):
   q=copy.deepcopy(r);q['walkGarment']['sourceHemMode']=value
   with self.assertRaises(ValueError):validate(q)
  r['walkGarment']['sourceHemMode']='preserve-x';del r['walkGarment']['hemConnection']
  with self.assertRaises(ValueError):validate(r)

class SparseSourceHemGuardTests(unittest.TestCase):
 def fixture(self,active_fold=False):
  import math
  import numpy as np
  from PIL import Image,ImageDraw
  r,l=test_garment.GarmentTests().fixture();r['walkGarment'].update(sourceHemMode='preserve-x',hemConnection={'mode':'skin-mesh','overlap':1})
  for side,p in r['walkGarment']['panels'].items():
   x0,y0,x1,y1=p['sourceBox'];im=Image.new('RGBA',(384,384));ImageDraw.Draw(im).rectangle((x0 if active_fold else x0+8,y0+3,x1-8,y1-3),fill=(50,40,30,255));l['walk:garment_'+side]=im
  transforms={n:(p['start'],math.atan2(p['end'][1]-p['start'][1],p['end'][0]-p['start'][0])) for n,p in r['parts'].items()}
  def mapper_factory(rig,transforms,parent,*args,**kwargs):
   panel=rig['walkGarment']['panels'][parent.split('_')[0]];x0,y0,x1,y1=panel['sourceBox']
   return lambda v:np.array([v[0],y0-10 if v[0]<x0+4 else v[1]],float)
  return r,l,transforms,mapper_factory
 def test_empty_corner_fold_deferred_to_real_active_mesh(self):
  from unittest.mock import patch
  from garment import apply_garment
  r,l,t,mapper=self.fixture();stats=[]
  with patch('garment.joint_mapper',side_effect=mapper):apply_garment(r,l,t,stats)
  mesh=[s for s in stats if s['side'].startswith('garment_mesh_')]
  self.assertEqual(len(mesh),2);self.assertTrue(all(s['activeInvertedTriangles']==0 and s['areaRatio']>=.08 for s in mesh))
  # Legacy remains conservative and rejects this enclosing quad.
  r['walkGarment'].pop('sourceHemMode')
  with patch('garment.joint_mapper',side_effect=mapper):
   with self.assertRaisesRegex(ValueError,'Garment panel folds/collapses'):apply_garment(r,l,t)
 def test_occupied_fold_still_rejected(self):
  from unittest.mock import patch
  from garment import apply_garment
  r,l,t,mapper=self.fixture(active_fold=True)
  with patch('garment.joint_mapper',side_effect=mapper):
   with self.assertRaisesRegex(ValueError,'Mapped garment folds/collapses'):apply_garment(r,l,t)
