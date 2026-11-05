import unittest,copy,math
from demo import demo
from motion import pose,render,render_neutral,validate
class KneeContourTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(gaitProfile='coupled-v2',walkStyle='simple',motionScale=.45,jointMeshes=[dict(parent=s+'_thigh',child=s+'_shin',radius=28) for s in ('left','right')]);n=copy.deepcopy(r)
  for m in n['jointMeshes']:m['walkContour']='centerline'
  return r,n,l
 def test_pose_neutral_dash_preserved(self):
  r,n,l=self.fixture();self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(n,l).tobytes())
  for i in range(8):
   self.assertEqual(pose(r,'walk',i/8),pose(n,'walk',i/8));self.assertEqual(render(r,l,'dash',i/8)[0].tobytes(),render(n,l,'dash',i/8)[0].tobytes())
 def test_finite_continuous_loop(self):
  r,n,l=self.fixture()
  for i in range(8):
   image,ds=render(n,l,'walk',i/8);self.assertEqual(image.size,(384,384))
   for d in ds:
    for m in d.get('jointMeshDiagnostics',[]):self.assertTrue(math.isfinite(m['minimumActiveAreaRatio']))
  self.assertEqual(render(n,l,'walk',0)[0].tobytes(),render(n,l,'walk',1)[0].tobytes())
 def test_invalid_modes_and_pair(self):
  r,n,l=self.fixture();n['jointMeshes'][0]['walkContour']='unknown'
  with self.assertRaisesRegex(ValueError,'walkContour'):validate(n)
  n['jointMeshes'][0]=dict(parent='left_upper_arm',child='left_forearm',radius=28,walkContour='centerline')
  with self.assertRaisesRegex(ValueError,'thigh/shin'):validate(n)
