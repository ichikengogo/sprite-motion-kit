import unittest,copy,math
from demo import demo
from motion import pose,gait_config,validate,render_neutral
class UprightTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',motionScale=.48,facing='left',armMotion='shoulder-led',legSwing='thigh-led');return r,{**r,'walkPosture':'upright'},l
 def test_bones_and_less_drop(self):
  old,r,_=self.fixture();reductions=[]
  for i in range(8):
   t,d=pose(r,'walk',i/8);ot,_=pose(old,'walk',i/8);reductions.append(ot['head'][0][1]-t['head'][0][1])
   for x in d:
    self.assertAlmostEqual(math.dist(x['hip'],x['knee']),x['lengths'][0]);self.assertAlmostEqual(math.dist(x['knee'],x['ankle']),x['lengths'][1]);self.assertLess(x['reach_error'],1e-6)
  self.assertGreater(sum(reductions)/len(reductions),1)
 def test_walking_support_pitch_and_loop(self):
  _,r,_=self.fixture();ts=[]
  for i in range(24):
   t,d=pose(r,'walk',i/24);ts.append(t);self.assertGreaterEqual(sum(x['contact'] for x in d),1)
  self.assertEqual(len({t['head'][1] for t in ts}),1);self.assertLess(max(t['head'][0][0] for t in ts)-min(t['head'][0][0] for t in ts),1e-8);self.assertEqual(pose(r,'walk',0),pose(r,'walk',1))
  for p in [0,.1,.125,.25,.35,.5,.6,.75,.85]:
   a=pose(r,'walk',p-1e-7)[0];b=pose(r,'walk',p+1e-7)[0];self.assertLess(max(math.dist(a[n][0],b[n][0]) for n in a),.001)
 def test_legacy_dash_neutral_and_small_stride_tradeoff(self):
  old,r,l=self.fixture()
  for i in range(8):self.assertEqual(pose(old,'dash',i/8),pose(r,'dash',i/8));self.assertEqual(pose(old,'walk',i/8),pose({**old,'walkPosture':'legacy'},'walk',i/8))
  self.assertEqual(render_neutral(old,l).tobytes(),render_neutral(r,l).tobytes());self.assertEqual(gait_config(r,'walk')['duration'],1);self.assertEqual(gait_config(r,'walk')['stride']/gait_config(old,'walk')['stride'],160/170)
 def test_invalid(self):
  _,r,_=self.fixture()
  for p in [{'view':'front'},{'walkStyle':'purposeful'},{'walkPosture':'bad'}]:
   with self.assertRaises(ValueError):validate({**r,**p})
