import unittest,math
from demo import demo
from motion import pose,render_neutral,validate,limit_recovery_bend,foot_path,gait_config
class ThighRecoveryTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',motionScale=.48,facing='left',armMotion='shoulder-led');return r,{**r,'legSwing':'thigh-led'},l
 def test_earlier_thigh_and_soft_knee_cap(self):
  r,n,_=self.fixture()
  for phase,side in [(.25,'right'),(.75,'left')]:
   self.assertGreater(pose(n,'walk',phase)[0][side+'_thigh'][1],pose(r,'walk',phase)[0][side+'_thigh'][1])
  for i in range(97):
   t,ds=pose(n,'walk',i/96)
   for d in ds:
    if not d['contact']:
     s=d['side'];bend=(t[s+'_shin'][1]-t[s+'_thigh'][1]+math.pi)%(2*math.pi)-math.pi;self.assertLessEqual(abs(bend),math.radians(75)+1e-9)
    self.assertAlmostEqual(math.dist(d['hip'],d['knee']),d['lengths'][0]);self.assertAlmostEqual(math.dist(d['knee'],d['ankle']),d['lengths'][1])
 def test_support_dash_neutral_and_legacy(self):
  r,n,l=self.fixture()
  for i in range(24):
   phase=i/24
   for side,index in [('left',0),('right',1)]:
    a=foot_path(r,side,index,phase,gait_config(r,'walk'),'walk');b=foot_path(n,side,index,phase,gait_config(n,'walk'),'walk')
    if a['contact']:self.assertEqual(a,b)
   self.assertEqual(pose(r,'dash',phase),pose(n,'dash',phase));self.assertEqual(pose(r,'walk',phase),pose({**r,'legSwing':'legacy'},'walk',phase))
  self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(n,l).tobytes())
 def test_cap_continuity_and_loop(self):
  for degrees in [65,85]:
   x=math.radians(degrees);eps=1e-6;self.assertLess(abs(limit_recovery_bend(x+eps)-limit_recovery_bend(x-eps)),3*eps)
  self.assertAlmostEqual(limit_recovery_bend(math.radians(30)),math.radians(30));self.assertAlmostEqual(limit_recovery_bend(math.radians(-100)),math.radians(-75))
  _,n,_=self.fixture();self.assertEqual(pose(n,'walk',0),pose(n,'walk',1))
 def test_invalid_profile(self):
  _,n,_=self.fixture()
  for patch in [{'view':'front'},{'walkStyle':'wide-stable'},{'legSwing':'unknown'}]:
   with self.assertRaises(ValueError):validate({**n,**patch})
