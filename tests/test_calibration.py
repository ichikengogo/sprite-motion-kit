import unittest,copy,math
from demo import demo
from motion import pose,validate
class CalibrationTests(unittest.TestCase):
 def test_motion_scale_changes_trajectory_not_bone_lengths(self):
  _,r,_=demo('side');small=copy.deepcopy(r);small.update(motionScale=.4,pelvisDrop=6)
  for action in ('walk','dash'):
   _,a=pose(r,action,0);_,b=pose(small,action,0)
   neutral=r['parts']['left_shin']['end'][0]
   self.assertAlmostEqual(b[0]['target'][0]-neutral,.4*(a[0]['target'][0]-neutral))
   for i in range(24):
    _,d=pose(small,action,i/24)
    for leg in d:
     self.assertAlmostEqual(math.dist(leg['hip'],leg['knee']),leg['lengths'][0]);self.assertAlmostEqual(math.dist(leg['knee'],leg['ankle']),leg['lengths'][1])
  self.assertEqual(pose(small,'walk',0),pose(small,'walk',1))
 def test_invalid_calibration_is_rejected(self):
  for key,value in [('motionScale',0),('motionScale',3),('motionScale',True),('pelvisDrop',-1),('pelvisDrop',21),('pelvisDrop',float('nan'))]:
   _,r,_=demo('side');r[key]=value
   with self.assertRaises(ValueError):validate(r)
