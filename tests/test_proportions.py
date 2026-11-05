import unittest,copy,math
import numpy as np
from PIL import Image,ImageDraw
import test_garment
from motion import validate,pose,render,render_neutral,export
from proportions import active_rig,source_point,widen_source,display_point,display_image
class ProportionTests(unittest.TestCase):
 def fixture(self):
  r,l=test_garment.GarmentTests().fixture();r['walkProportions']={'confirmed':True,'legScale':1.1,'bodyRise':0,'width':{'amount':.1,'hemHold':3,'ramp':6,'endY':295,'fade':9,'kneeReduction':.3,'kneeRadius':4},'display':{'scale':.95,'anchor':[192,349]}};return r,l
 def test_gate_and_limits(self):
  r,l=self.fixture();validate(r)
  for key,val in [('confirmed','true'),('confirmed',False),('legScale',float('nan')),('legScale',2),('bodyRise',-1)]:
   q=copy.deepcopy(r);q['walkProportions'][key]=val
   with self.assertRaises(ValueError):validate(q)
  for key,val in [('amount',.8),('endY',384),('ramp',0)]:
   q=copy.deepcopy(r);q['walkProportions']['width'][key]=val
   with self.assertRaises(ValueError):validate(q)
  q=copy.deepcopy(r);q['walkProportions']['display']['scale']=0
  with self.assertRaises(ValueError):validate(q)
 def test_leg_lengths_shoes_rigid_body_and_dash(self):
  r,l=self.fixture();old=copy.deepcopy(r);del old['walkProportions']
  for i in range(25):
   t,d=pose(r,'walk',i/24);base,_=pose(old,'walk',i/24)
   for s in ['left','right']:
    for a,b,n in [('thigh','shin','thigh'),('shin','foot','shin')]:
     expected=np.linalg.norm(np.array(r['parts'][s+'_'+n]['end'])-r['parts'][s+'_'+n]['start'])*1.1;self.assertAlmostEqual(np.linalg.norm(np.array(t[s+'_'+b][0])-t[s+'_'+a][0]),expected)
    self.assertTrue(np.allclose(t[s+'_foot'][0],base[s+'_foot'][0]));self.assertEqual(t[s+'_foot'][1],base[s+'_foot'][1])
   for n in ['head','torso','left_upper_arm','right_forearm']:self.assertEqual(t[n],base[n])
   self.assertEqual(pose(r,'dash',i/24),pose(old,'dash',i/24))
  self.assertEqual(render(r,l,'dash',0)[0].tobytes(),render(old,l,'dash',0)[0].tobytes())
 def test_fixed_display_transform_no_bbox_fit(self):
  r,l=self.fixture();r=active_rig(r,'walk');im=Image.new('RGBA',(384,384));ImageDraw.Draw(im).rectangle((100,100,200,300),fill='red');s=.95;x,y=192,349
  expected=im.transform((384,384),Image.Transform.AFFINE,(1/s,0,x*(1-1/s),0,1/s,y*(1-1/s)),Image.Resampling.BICUBIC);self.assertEqual(display_image(r,im).tobytes(),expected.tobytes());self.assertTrue(np.allclose(display_point(r,[192,349]),[192,349]));self.assertEqual(display_image(active_rig(r,'dash'),im).tobytes(),im.tobytes())
 def test_source_width_protects_hem_and_ankle(self):
  r,l=self.fixture()
  for side in ['left','right']:
   start=r['walkGarment']['panels'][side]['skinStart']
   for y in [start,start+2,295,310,340]:
    p=np.array([190.,y]);self.assertTrue(np.allclose(widen_source(r,side,p),p))
   for name in ['thigh','shin']:
    p=r['parts'][side+'_'+name];self.assertAlmostEqual(np.linalg.norm(source_point(r,side,p['end'])-source_point(r,side,p['start'])),1.1*np.linalg.norm(np.array(p['end'])-p['start']))
 def test_roundtrip_metadata_nonmutation_loop(self):
  import json
  r,l=self.fixture();old=copy.deepcopy(r);saved={k:v.tobytes() for k,v in l.items()};r=json.loads(json.dumps(r));sheet,m=export(r,l,'walk');self.assertEqual(m['walkProportions'],r['walkProportions']);self.assertEqual(m['sourceRootPivot'],r['root']);self.assertEqual(len(m['frames']),8);self.assertEqual(r,old);self.assertEqual(saved,{k:v.tobytes() for k,v in l.items()});self.assertEqual(render(r,l,'walk',0)[0].tobytes(),render(r,l,'walk',1)[0].tobytes());self.assertEqual(render_neutral(r,l).size,(384,384))
 def test_unreachable_rise_is_not_silent_clamp(self):
  r,l=self.fixture();r['walkProportions']['bodyRise']=60
  with self.assertRaises(ValueError):render(r,l,'walk',0)
