import unittest,copy
from PIL import Image
from demo import demo
from motion import render,render_neutral,pose,export,validate
from hip_cloth import prepare
class HipOverlapTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',hipAttachment={'mode':'split-cloth','confirmed':True});r['jointMeshes']=[{'parent':s+'_thigh','child':s+'_shin','radius':10} for s in ['left','right']];l.update({'walk:'+s+'_thigh':l[s+'_thigh'].copy() for s in ['left','right']});n=copy.deepcopy(r);n['hipAttachment']['rootOverlap']=True
  for s in ['left','right']:
   im=Image.new('RGBA',(384,384),(95,75,60,255));im.putalpha(l[s+'_thigh'].getchannel('A'));l['walk:'+s+'_hip']=im
  return r,n,l
 def test_order_no_added_limb_warp_and_nonmutation(self):
  _,r,l=self.fixture();original=copy.deepcopy(r);old=l['right_thigh'].tobytes();t,_=pose(r,'walk',.25);rr,ll,tt=prepare(r,l,t);self.assertGreater(rr['order'].index('pelvis'),rr['order'].index('right_thigh'));self.assertNotIn('waistAttachment',rr);self.assertEqual(r,original);self.assertEqual(old,l['right_thigh'].tobytes());self.assertEqual(tt['right_thigh'],t['right_thigh'])
 def test_material_required_and_alpha_fixed(self):
  _,r,l=self.fixture();bad=dict(l);bad.pop('walk:left_hip')
  with self.assertRaises(ValueError):render(r,bad,'walk',0)
  bad=dict(l);bad['walk:left_hip']=Image.new('RGBA',(384,384),'red')
  with self.assertRaises(ValueError):render(r,bad,'walk',0)
  r['hipAttachment']['rootOverlap']='true'
  with self.assertRaises(ValueError):validate(r)
 def test_action_pose_neutral_and_default_preserved(self):
  old,new,l=self.fixture()
  for t in [0,.25,.5,.75]:self.assertEqual(pose(old,'walk',t),pose(new,'walk',t));self.assertEqual(render(old,l,'dash',t)[0].tobytes(),render(new,l,'dash',t)[0].tobytes())
  self.assertEqual(render_neutral(old,l).tobytes(),render_neutral(new,l).tobytes());self.assertEqual(render(new,l,'walk',0)[0].tobytes(),render(new,l,'walk',1)[0].tobytes());legacy=copy.deepcopy(old);legacy['hipAttachment']['rootOverlap']=False;self.assertEqual(render(old,l,'walk',.25)[0].tobytes(),render(legacy,l,'walk',.25)[0].tobytes())
 def test_export_disclosure(self):
  _,r,l=self.fixture();_,m=export(r,l,'walk');self.assertTrue(m['hipRootOverlap']);self.assertIn('left_hip',m['walkMaterialParts']);self.assertEqual(len(m['frames']),8)
