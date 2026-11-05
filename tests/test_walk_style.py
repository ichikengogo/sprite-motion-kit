import unittest,copy,math
from demo import demo
from motion import pose,render,render_neutral,gait_config,validate
class WalkStyleTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(gaitProfile='coupled-v2',motionScale=.48,preserveReach=True);return r,l
 def test_style_changes_stride_not_period_or_flight(self):
  r,l=self.fixture();b=copy.deepcopy(r);b['walkStyle']='purposeful'
  self.assertEqual(gait_config(r,'walk')['duration'],gait_config(b,'walk')['duration'])
  for rig in [r,b]:self.assertTrue(all(any(d['contact'] for d in pose(rig,'walk',i/240)[1]) for i in range(240)))
  def travel(rig):
   xs=[pose(rig,'walk',i/48)[1][0]['target'][0] for i in range(48)];return max(xs)-min(xs)
  self.assertGreater(travel(b),travel(r)*1.5)
  self.assertLess(gait_config(b,'walk')['lift'],gait_config(r,'walk')['lift'])
 def test_dash_and_neutral_unchanged(self):
  r,l=self.fixture();b={**r,'walkStyle':'purposeful'}
  for i in range(24):self.assertEqual(pose(r,'dash',i/24),pose(b,'dash',i/24))
  self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(b,l).tobytes())
  self.assertEqual(render(r,l,'dash',.25)[0].tobytes(),render(b,l,'dash',.25)[0].tobytes())
 def test_soft_extension_loop_and_boundaries(self):
  r,l=self.fixture();r['walkStyle']='purposeful'
  for t in [0,.1,.35,.5,.6]:
   a=pose(r,'walk',t-1e-7)[0];b=pose(r,'walk',t+1e-7)[0]
   self.assertLess(max(math.dist(a[n][0],b[n][0]) for n in a),.001)
  self.assertEqual(render(r,l,'walk',0)[0].tobytes(),render(r,l,'walk',1)[0].tobytes())
 def test_unknown_style_rejected(self):
  r,l=self.fixture();r['walkStyle']='automaticanything'
  with self.assertRaises(ValueError):validate(r)
