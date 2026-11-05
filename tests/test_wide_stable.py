import unittest,math
from demo import demo
from motion import pose,render,render_neutral,gait_config
class WideStableTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(gaitProfile='coupled-v2',motionScale=.48,preserveReach=True,walkStyle='purposeful');return r,l
 def test_wider_step_and_fixed_upperbody_pitch(self):
  r,l=self.fixture();wide={**r,'walkStyle':'wide-stable'}
  old=[pose(r,'walk',i/48) for i in range(48)];new=[pose(wide,'walk',i/48) for i in range(48)]
  self.assertGreater(max(x[0]['head'][0][0] for x in old)-min(x[0]['head'][0][0] for x in old),1)
  for name in ('head','torso'):
   self.assertLess(max(x[0][name][0][0] for x in new)-min(x[0][name][0][0] for x in new),1e-9)
   self.assertLess(max(x[0][name][1] for x in new)-min(x[0][name][1] for x in new),1e-9)
  travel=lambda frames:max(x[1][0]['target'][0] for x in frames)-min(x[1][0]['target'][0] for x in frames)
  self.assertGreater(travel(new),travel(old)*1.25)
 def test_contact_bones_and_smooth_loop(self):
  r,l=self.fixture();r['walkStyle']='wide-stable'
  for i in range(97):
   _,ds=pose(r,'walk',i/96);self.assertTrue(any(d['contact'] for d in ds))
   for d in ds:
    self.assertAlmostEqual(math.dist(d['hip'],d['knee']),d['lengths'][0]);self.assertAlmostEqual(math.dist(d['knee'],d['ankle']),d['lengths'][1]);self.assertLess(d['reach_error'],1e-5)
  for t in (0,.1,.35,.5,.6):
   a=pose(r,'walk',t-1e-7)[0];b=pose(r,'walk',t+1e-7)[0];self.assertLess(max(math.dist(a[n][0],b[n][0]) for n in a),.001)
  self.assertEqual(render(r,l,'walk',0)[0].tobytes(),render(r,l,'walk',1)[0].tobytes())
 def test_dash_neutral_and_period_unchanged(self):
  r,l=self.fixture();wide={**r,'walkStyle':'wide-stable'}
  for i in range(24):self.assertEqual(pose(r,'dash',i/24),pose(wide,'dash',i/24))
  self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(wide,l).tobytes());self.assertEqual(gait_config(r,'walk')['duration'],gait_config(wide,'walk')['duration'])
