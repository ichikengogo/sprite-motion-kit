import unittest,copy,math
from demo import demo
from motion import render,render_neutral,pose,export,validate,compose_pose
class AnkleAttachmentTests(unittest.TestCase):
 def fixture(self):
  _,old,l=demo('side');old['walkStyle']='simple';old['jointMeshes']=[{'parent':s+'_thigh','child':s+'_shin','radius':10} for s in ['left','right']];new=copy.deepcopy(old)
  for m in new['jointMeshes']:m['walkAnkleDepth']=24
  return old,new,l
 def test_validation(self):
  _,r,_=self.fixture();validate(r)
  for value in [True,-1,2,25,float('nan'),'24']:
   bad=copy.deepcopy(r);bad['jointMeshes'][0]['walkAnkleDepth']=value
   with self.assertRaises(ValueError):validate(bad)
  r['view']='front'
  with self.assertRaises(ValueError):validate(r)
 def test_pose_shoe_dash_neutral_preserved(self):
  old,new,l=self.fixture()
  for t in [0,.125,.25,.5,.75,1]:
   self.assertEqual(pose(old,'walk',t),pose(new,'walk',t))
   self.assertEqual(render(old,l,'dash',t)[0].tobytes(),render(new,l,'dash',t)[0].tobytes())
   for s in ['left','right']:
    a=copy.deepcopy(old);b=copy.deepcopy(new)
    for r in [a,b]:r['order']=[s+'_foot'];r['jointMeshes']=[]
    tr,_=pose(old,'walk',t);self.assertEqual(compose_pose(a,l,tr,action='walk').tobytes(),compose_pose(b,l,tr,action='walk').tobytes())
  self.assertEqual(render_neutral(old,l).tobytes(),render_neutral(new,l).tobytes())
  self.assertEqual(render(new,l,'walk',0)[0].tobytes(),render(new,l,'walk',1)[0].tobytes())
 def test_no_mutation_and_export(self):
  old,r,l=self.fixture();saved=copy.deepcopy(r);pixels={k:v.tobytes() for k,v in l.items()};_,meta=export(r,l,'walk');self.assertEqual(r,saved);self.assertEqual(pixels,{k:v.tobytes() for k,v in l.items()});self.assertEqual(len(meta['walkAnkleAttachments']),2);self.assertEqual(meta['fps'],8)
 def test_neutral_transform_identity(self):
  from joint_mesh import draw_joint
  old,r,l=self.fixture();tr={n:(p['start'],math.atan2(p['end'][1]-p['start'][1],p['end'][0]-p['start'][0])) for n,p in r['parts'].items()}
  for s in ['left','right']:
   self.assertEqual(draw_joint(r,l,tr,s+'_thigh',s+'_shin',10).tobytes(),draw_joint(r,l,tr,s+'_thigh',s+'_shin',10,ankle_depth=24).tobytes())
