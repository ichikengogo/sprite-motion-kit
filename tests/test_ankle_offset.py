import unittest,copy,math
from demo import demo
from motion import validate,pose,render,render_neutral,export
class AnkleOffsetTests(unittest.TestCase):
 def fixture(self):
  _,old,l=demo('side');old['walkStyle']='simple';old['jointMeshes']=[{'parent':s+'_thigh','child':s+'_shin','radius':10,'walkAnkleDepth':24} for s in ['left','right']];new=copy.deepcopy(old);new['jointMeshes'][0]['walkAnkleOffsetX']=-2;return old,new,l
 def test_validation(self):
  _,r,_=self.fixture();validate(r)
  for v in [True,-5,5,float('nan'),'2']:
   b=copy.deepcopy(r);b['jointMeshes'][0]['walkAnkleOffsetX']=v
   with self.assertRaises(ValueError):validate(b)
  r['jointMeshes'][0]['walkAnkleDepth']=0
  with self.assertRaises(ValueError):validate(r)
 def test_pose_dash_neutral_loop_and_default(self):
  old,new,l=self.fixture()
  for t in [0,.125,.25,.5,.75]:
   self.assertEqual(pose(old,'walk',t),pose(new,'walk',t));self.assertEqual(render(old,l,'dash',t)[0].tobytes(),render(new,l,'dash',t)[0].tobytes())
  self.assertEqual(render_neutral(old,l).tobytes(),render_neutral(new,l).tobytes());self.assertEqual(render(new,l,'walk',0)[0].tobytes(),render(new,l,'walk',1)[0].tobytes());zero=copy.deepcopy(old);zero['jointMeshes'][0]['walkAnkleOffsetX']=0;self.assertEqual(render(zero,l,'walk',.25)[0].tobytes(),render(old,l,'walk',.25)[0].tobytes())
 def test_source_unchanged_and_export(self):
  _,r,l=self.fixture();before=copy.deepcopy(r);pixels={k:v.tobytes() for k,v in l.items()};_,m=export(r,l,'walk');self.assertEqual(m['walkAnkleAttachments'][0]['offsetX'],-2);self.assertEqual(r,before);self.assertEqual(pixels,{k:v.tobytes() for k,v in l.items()})
 def test_rigid_shoe_transform_unchanged(self):
  from motion import compose_pose
  old,new,l=self.fixture()
  for t in [0,.125,.375,.625,.875]:
   tr,_=pose(old,'walk',t)
   for r in [old,new]:r['order']=['left_foot'];r['jointMeshes']=[]
   self.assertEqual(compose_pose(old,l,tr,action='walk').tobytes(),compose_pose(new,l,tr,action='walk').tobytes())
