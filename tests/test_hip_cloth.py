import unittest,copy,math
from demo import demo
from motion import validate,pose,render,render_neutral,export
from hip_cloth import prepare
class HipClothTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',motionScale=.48,hipAttachment={'mode':'split-cloth','confirmed':True});r['jointMeshes']=[{'parent':s+'_thigh','child':s+'_shin','radius':10} for s in ('left','right')]
  l.update({'walk:'+s+'_thigh':l[s+'_thigh'].copy() for s in ('left','right')});return r,l
 def test_missing_and_unconfirmed(self):
  r,l=self.fixture();validate(r)
  for patch in [{'confirmed':False},{'mode':'bad'},{'capEnd':float('nan')},{'bottomRotation':True}]:
   bad=copy.deepcopy(r);bad['hipAttachment'].update(patch)
   with self.assertRaises(ValueError):validate(bad)
  l.pop('walk:left_thigh')
  with self.assertRaises(ValueError):render(r,l,'walk',0)
 def test_does_not_mutate_pose_dash_neutral(self):
  r,l=self.fixture();old=copy.deepcopy(r);old.pop('hipAttachment');snapshot=copy.deepcopy(r)
  for i in range(8):self.assertEqual(pose(r,'walk',i/8),pose(old,'walk',i/8))
  self.assertEqual(render(r,l,'dash',0)[0].tobytes(),render(old,l,'dash',0)[0].tobytes());self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(old,l).tobytes());self.assertEqual(r,snapshot)
 def test_bridge_neutral_and_loop(self):
  r,l=self.fixture();t={n:(p['start'],math.atan2(p['end'][1]-p['start'][1],p['end'][0]-p['start'][0])) for n,p in r['parts'].items()};stats=[];rr,ll,tt=prepare(r,l,t,stats)
  for d in stats:self.assertAlmostEqual(d['areaRatio'],1);self.assertGreater(d['minCornerCross'],0)
  self.assertNotIn('pelvis',r['parts']);self.assertIn('pelvis',rr['parts']);self.assertEqual(render(r,l,'walk',0)[0].tobytes(),render(r,l,'walk',1)[0].tobytes())
 def test_export_with_alternate_layers(self):
  r,l=self.fixture();sheet,meta=export(r,l,'walk');self.assertEqual(len(meta['frames']),8);self.assertEqual(meta['hipCloth'],'split-cloth');self.assertEqual(meta['duration'],1)
 def test_invalid_context_and_fold(self):
  r,l=self.fixture()
  for patch in [{'view':'front'},{'walkStyle':'cautious'},{'jointMeshes':[]}]:
   with self.assertRaises(ValueError):validate({**r,**patch})
  t,_=pose(r,'walk',0);t['left_thigh']=(t['left_thigh'][0],-math.pi/2)
  with self.assertRaises(ValueError):prepare(r,l,t)
