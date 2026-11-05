import unittest,copy,math
from PIL import Image
from demo import demo
from motion import validate,pose,render,render_neutral,export
from hip_cloth import prepare
class ClothWidthTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',hipAttachment={'mode':'split-cloth','confirmed':True});r['jointMeshes']=[{'parent':s+'_thigh','child':s+'_shin','radius':10} for s in ['left','right']];l.update({'walk:'+s+'_thigh':l[s+'_thigh'].copy() for s in ['left','right']});n=copy.deepcopy(r);hip=r['parts']['left_thigh']['start'][1];knee=r['parts']['left_shin']['start'][1];n['jointMeshes'][0]['walkClothWidth']={'scale':.82,'fullUntil':hip+(knee-hip)*.55,'fadeEnd':hip+(knee-hip)*.75};return r,n,l
 def test_validation(self):
  _,r,_=self.fixture();validate(r)
  for shape in [{'scale':.5,'fullUntil':250,'fadeEnd':260},{'scale':True,'fullUntil':250,'fadeEnd':260},{'scale':.82,'fullUntil':260,'fadeEnd':250},{'scale':.82,'fullUntil':250,'fadeEnd':384},{'scale':.82,'fullUntil':250,'fadeEnd':251},{'scale':float('nan'),'fullUntil':250,'fadeEnd':260},{}]:
   b=copy.deepcopy(r);b['jointMeshes'][0]['walkClothWidth']=shape
   with self.assertRaises(ValueError):validate(b)
  r.pop('hipAttachment')
  with self.assertRaises(ValueError):validate(r)
 def test_action_pose_neutral_loop_preservation(self):
  old,new,l=self.fixture()
  for t in [0,.125,.25,.5,.75]:
   self.assertEqual(pose(old,'walk',t),pose(new,'walk',t));self.assertEqual(render(old,l,'dash',t)[0].tobytes(),render(new,l,'dash',t)[0].tobytes())
  self.assertEqual(render_neutral(old,l).tobytes(),render_neutral(new,l).tobytes());self.assertEqual(render(new,l,'walk',0)[0].tobytes(),render(new,l,'walk',1)[0].tobytes());self.assertNotEqual(render(old,l,'walk',.25)[0].tobytes(),render(new,l,'walk',.25)[0].tobytes())
 def test_lower_cap_matches_width_without_top_or_pose_change(self):
  old,new,l=self.fixture();tr,_=pose(old,'walk',.125);a=[];b=[];prepare(old,l,tr,a);prepare(new,l,tr,b);a=a[0];b=b[0]
  self.assertEqual(a['sourceQuad'],b['sourceQuad']);self.assertEqual(a['destinationQuad'][:2],b['destinationQuad'][:2]);wa=math.dist(*a['destinationQuad'][2:]);wb=math.dist(*b['destinationQuad'][2:]);self.assertAlmostEqual(wb/wa,.82,places=10);self.assertGreater(b['areaRatio'],0)
 def test_export_disclosure_nonmutation(self):
  _,r,l=self.fixture();before=copy.deepcopy(r);pixels={k:v.tobytes() for k,v in l.items()};_,meta=export(r,l,'walk');self.assertEqual(meta['walkClothWidths'][0]['scale'],.82);self.assertEqual(meta['fps'],8);self.assertEqual(r,before);self.assertEqual(pixels,{k:v.tobytes() for k,v in l.items()})
