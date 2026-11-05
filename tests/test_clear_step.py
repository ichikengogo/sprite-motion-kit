import math,unittest
from demo import demo
from motion import pose,validate,limit_recovery_bend,render_neutral,export
class ClearStepTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',walkPosture='upright',legSwing='thigh-led',armMotion='shoulder-led',motionScale=.48,facing='left');return r,{**r,'legRecovery':'clear-step'},l
 def test_support_body_bones_and_dash_unchanged(self):
  old,new,l=self.fixture()
  for i in range(49):
   p=i/48;a,da=pose(old,'walk',p);b,db=pose(new,'walk',p)
   for n in ['head','torso']:self.assertEqual(a[n],b[n])
   for d in db:
    s=d['side']
    if d['contact']:
     for n in ['thigh','shin','foot']:self.assertEqual(a[s+'_'+n],b[s+'_'+n])
    else:
     q=((p+(0 if s=='left' else .5))%1-.6)/.4
     if .15<=q<=.85:self.assertLessEqual(abs((b[s+'_shin'][1]-b[s+'_thigh'][1]+math.pi)%(2*math.pi)-math.pi),math.radians(55)+1e-9)
    self.assertAlmostEqual(math.dist(d['hip'],d['knee']),d['lengths'][0]);self.assertAlmostEqual(math.dist(d['knee'],d['ankle']),d['lengths'][1])
   self.assertEqual(pose(old,'dash',p),pose(new,'dash',p))
  self.assertEqual(render_neutral(old,l).tobytes(),render_neutral(new,l).tobytes())
 def test_default_loop_and_boundary_continuity(self):
  old,new,_=self.fixture();self.assertEqual(pose(old,'walk',.25),pose({**old,'legRecovery':'legacy'},'walk',.25));self.assertEqual(pose(new,'walk',0),pose(new,'walk',1))
  for i in range(101):
   a=pose(new,'walk',i/100-1e-7)[0];b=pose(new,'walk',i/100+1e-7)[0];self.assertLess(max(math.dist(a[n][0],b[n][0]) for n in a),.001)
  for deg in [45,65]:
   x=math.radians(deg);self.assertLess(abs(limit_recovery_bend(x+1e-7,55)-limit_recovery_bend(x-1e-7,55)),3e-7)
 def test_validation_and_export(self):
  _,r,l=self.fixture();validate(r)
  for patch in [{'view':'front'},{'walkStyle':'wide-stable'},{'legSwing':'legacy'},{'legRecovery':'unknown'}]:
   with self.assertRaises(ValueError):validate({**r,**patch})
  _,m=export(r,l,'walk');self.assertEqual(m['legRecovery'],'clear-step');self.assertEqual(len(m['frames']),8);self.assertEqual(m['duration'],1)
