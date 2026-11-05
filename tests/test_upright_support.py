import unittest,math
from demo import demo
from motion import pose,validate
class UprightSupportTests(unittest.TestCase):
 def straight_rig(self):
  _,r,_=demo('side')
  for side in ('left','right'):
   hip=r['parts'][side+'_thigh']['start'];ankle=r['parts'][side+'_shin']['end'];knee=[(hip[0]+ankle[0])/2,(hip[1]+ankle[1])/2]
   r['parts'][side+'_thigh']['end']=knee;r['parts'][side+'_shin']['start']=knee
  return r
 def test_adaptive_support_avoids_stretch_without_constant_crouch(self):
  r=self.straight_rig();r['motionScale']=.28;r['preserveReach']=True
  for action in ('walk','dash'):
   corrections=[]
   for i in range(121):
    _,legs=pose(r,action,i/120)
    for d in legs:
     self.assertLess(d['reach_error'],1e-7);self.assertAlmostEqual(math.dist(d['hip'],d['knee']),d['lengths'][0]);self.assertAlmostEqual(math.dist(d['knee'],d['ankle']),d['lengths'][1]);corrections.append(d['supportCorrectionPx'])
   self.assertLess(max(corrections),6);self.assertGreater(max(corrections)-min(corrections),.1)
   self.assertEqual(pose(r,action,0),pose(r,action,1))
 def test_defaults_and_bad_values(self):
  _,r,_=demo('side');a=pose(r,'walk',.2);r.update(preserveReach=False,armSwingScale=1.0);self.assertEqual(a,pose(r,'walk',.2))
  for field,value in [('preserveReach','true'),('armSwingScale',-1),('armSwingScale',2),('armSwingScale',True)]:
   _,r,_=demo('side');r[field]=value
   with self.assertRaises(ValueError):validate(r)
