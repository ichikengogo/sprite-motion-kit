import unittest,copy,math
import numpy as np
from PIL import Image,ImageDraw
import test_garment_seams
from motion import validate,pose,render
from hip_cloth import prepare
from seam_quality import measure_upper_seam
class WaistConnectionTests(unittest.TestCase):
 def fixture(self):
  r,l=test_garment_seams.GarmentSeamTests().fixture();c=r['walkGarment'];c['hemConnection']={'mode':'skin-mesh','overlap':2};x=min(p['sourceBox'][0] for p in c['panels'].values());c['waistConnection']={'mode':'front-tube','topLift':3,'depth':18,'sourceFrontX':x-2,'fadeX':x+26};return r,l
 def test_bad_registration_rejected(self):
  r,l=self.fixture();validate(r)
  for k,v in [('topLift',float('nan')),('topLift',5),('depth',0),('sourceFrontX',384),('mode','fill')]:
   q=copy.deepcopy(r);q['walkGarment']['waistConnection'][k]=v
   with self.assertRaises(ValueError):validate(q)
  q=copy.deepcopy(r);del q['walkGarment']['hemConnection']
  with self.assertRaises(ValueError):validate(q)
 def test_pose_dash_assets_unchanged(self):
  r,l=self.fixture();old=copy.deepcopy(r);del old['walkGarment']['waistConnection'];before={k:v.tobytes() for k,v in l.items()}
  for t in [0,.25,.5,.75,1]:self.assertEqual(pose(r,'walk',t),pose(old,'walk',t))
  self.assertEqual(render(r,l,'dash',0)[0].tobytes(),render(old,l,'dash',0)[0].tobytes());prepare(r,l,pose(r,'walk',.5)[0]);self.assertEqual(before,{k:v.tobytes() for k,v in l.items()});self.assertNotIn('_garmentMeshBounds',r)
 def test_upper_silhouette_gap_not_hem_only(self):
  r,l=self.fixture();top=min(p['sourceBox'][1] for p in r['walkGarment']['panels'].values());x=min(p['sourceBox'][0] for p in r['walkGarment']['panels'].values());im=Image.new('RGBA',(384,384));ImageDraw.Draw(im).rectangle((x,top-12,x+23,top-3),fill=(20,20,20,255));l['torso']=im;t={n:(p['start'],math.atan2(p['end'][1]-p['start'][1],p['end'][0]-p['start'][0])) for n,p in r['parts'].items()}
  empty=measure_upper_seam(r,l,t,im);self.assertTrue(empty);self.assertEqual(min(v['alpha'] for v in empty),0)
  full=measure_upper_seam(r,l,t,Image.new('RGBA',(384,384),(20,20,20,255)));self.assertTrue(all(v['alpha']==255 for v in full))
 def test_loop_and_positive_cloth(self):
  r,l=self.fixture()
  for t in [0,.125,.25,.5,.625,.875,1]:
   stats=[];prepare(r,l,pose(r,'walk',t)[0],stats);waist=[x for x in stats if x['side']=='garment_waist'];self.assertEqual(len(waist),1);self.assertEqual(waist[0]['activeInvertedTriangles'],0);self.assertGreater(waist[0]['areaRatio'],.08)
  self.assertEqual(render(r,l,'walk',0)[0].tobytes(),render(r,l,'walk',1)[0].tobytes())
