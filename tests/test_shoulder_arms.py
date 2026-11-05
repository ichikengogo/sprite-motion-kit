import unittest,math
from demo import demo
from motion import pose,validate,render_neutral
class ShoulderArmTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',motionScale=.48);return r,l
 def test_light_fixed_bend_and_arm_lengths(self):
  r,_=self.fixture();r['armMotion']='shoulder-led'
  for i in range(25):
   t,ds=pose(r,'walk',i/24)
   for side,d in zip(('left','right'),ds):
    self.assertAlmostEqual(abs(t[side+'_forearm'][1]-t[side+'_upper_arm'][1]),.35)
    a=r['parts'][side+'_upper_arm'];b=r['parts'][side+'_forearm']
    self.assertAlmostEqual(math.dist(d['shoulder'],t[side+'_forearm'][0]),math.dist(a['start'],a['end']))
    self.assertAlmostEqual(math.dist(t[side+'_forearm'][0],d['wrist']),math.dist(b['start'],b['end']))
    self.assertEqual(d['armReachErrorPx'],0)
 def test_legs_body_dash_neutral_unchanged(self):
  r,l=self.fixture();new={**r,'armMotion':'shoulder-led'}
  for i in range(24):
   before=pose(r,'walk',i/24)[0];after=pose(new,'walk',i/24)[0]
   for name in before:
    if not name.endswith(('upper_arm','forearm')):self.assertEqual(before[name],after[name])
   self.assertEqual(pose(r,'dash',i/24),pose(new,'dash',i/24))
  self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(new,l).tobytes())
 def test_scale_loop_and_side_only(self):
  r,_=self.fixture();r['armMotion']='shoulder-led'
  def span(scale):
   a=[pose({**r,'armSwingScale':scale},'walk',i/24)[0]['right_upper_arm'][1] for i in range(24)];return max(a)-min(a)
  self.assertAlmostEqual(span(.5)*2,span(1));self.assertAlmostEqual(span(0),0)
  self.assertEqual(pose(r,'walk',0),pose(r,'walk',1))
  with self.assertRaisesRegex(ValueError,'side-view'):validate({**r,'view':'front'})
  with self.assertRaisesRegex(ValueError,'armMotion'):validate({**r,'armMotion':'unknown'})
