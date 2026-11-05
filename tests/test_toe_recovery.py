import unittest,math
from demo import demo
from motion import foot_path,gait_config,pose
class ToeRecoveryTests(unittest.TestCase):
 def fixture(self):
  _,r,_=demo('side');r.update(gaitProfile='coupled-v2',walkStyle='wide-stable',motionScale=.48,preserveReach=True,facing='left')
  for s in ('left','right'):
   p=r['parts'][s+'_foot'];x,y=p['start'];p['forefootContact']=[x-12,y+12];p['heelContact']=[x+4,y+12];p['soleOutline']=[[x-16,y+6],[x+6,y+6],[x+6,y+12],[x-16,y+12]]
  return r
 def test_swing_has_arc_and_early_toe_recovery(self):
  r=self.fixture();c=gait_config(r,'walk');p=r['parts']['left_foot'];ground=max(v[1] for v in p['soleOutline'])
  def clearance(t):
   f=foot_path(r,'left',0,t,c,'walk');roll=f['roll'];return ground-max(f['target'][1]+(v[0]-p['start'][0])*math.sin(roll)+(v[1]-p['start'][1])*math.cos(roll) for v in p['soleOutline'])
  self.assertGreater(clearance(.74),9);self.assertLess(clearance(.96),4)
  self.assertGreater(foot_path(r,'left',0,.74,c,'walk')['roll'],0)
  self.assertAlmostEqual(clearance(.3),0)
 def test_sole_slope_calibration_and_heel_landing(self):
  r=self.fixture();c=gait_config(r,'walk');p=r['parts']['left_foot'];flat=foot_path(r,'left',0,0,c,'walk')['roll'];p['forefootContact'][1]+=2
  tilted=foot_path(r,'left',0,0,c,'walk')['roll'];self.assertGreater(tilted,flat);self.assertLessEqual(tilted,.35)
 def test_pitch_transition_and_no_flight(self):
  r=self.fixture();c=gait_config(r,'walk')
  for t in (0,.6,.74,1):
   a=foot_path(r,'left',0,t-1e-7,c,'walk');b=foot_path(r,'left',0,t+1e-7,c,'walk');self.assertLess(abs(a['roll']-b['roll']),1e-5);self.assertLess(math.dist(a['target'],b['target']),.001)
  for i in range(97):self.assertTrue(any(x['contact'] for x in pose(r,'walk',i/96)[1]))
