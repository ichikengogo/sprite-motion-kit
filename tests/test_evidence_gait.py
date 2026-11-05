import unittest,math
from demo import demo
from motion import pose,foot_path,gait_config,render,validate
class EvidenceGaitTests(unittest.TestCase):
 def rig(self):
  _,r,l=demo('side');r['gaitProfile']='evidence-v1';r['motionScale']=.3
  for s in ('left','right'):
   p=r['parts'][s+'_foot'];x,y=p['start'];p['heelContact']=[x-4,y+6];p['forefootContact']=[x+17,y+6]
  return r,l
 def test_walk_double_support_and_dash_flight(self):
  r,_=self.rig()
  for action,flight,double in [('walk',0,.20),('dash',.32,0)]:
   counts=[sum(d['contact'] for d in pose(r,action,(i+.25)/1000)[1]) for i in range(1000)]
   self.assertAlmostEqual(counts.count(0)/1000,flight,places=2);self.assertAlmostEqual(counts.count(2)/1000,double,places=2)
 def test_opposite_body_vertical_phase(self):
  r,_=self.rig()
  for action in ('walk','dash'):
   stance=gait_config(r,action)['stance'];mid=pose(r,action,stance/2)[0]['torso'][0][1];transition=pose(r,action,(stance+.5)/2)[0]['torso'][0][1]
   if action=='walk':self.assertLess(mid,transition)
   else:self.assertGreater(mid,transition)
 def test_roll_about_contact_anchor_and_terminal_retraction(self):
  r,_=self.rig();cfg=gait_config(r,'walk');points=[]
  for t in (.40,.45,.55):
   p=foot_path(r,'left',0,t,cfg,'walk');self.assertEqual(p['contactMode'],'toe');self.assertGreater(p['roll'],0);self.assertLess(p['target'][1],r['parts']['left_shin']['end'][1]);points.append([p['contactPoint'][0]+p['ground_velocity']*t*cfg['duration'],p['contactPoint'][1]])
  for p in points:self.assertLess(math.dist(p,points[0]),1e-7)
  a=foot_path(r,'left',0,.992,cfg,'walk');b=foot_path(r,'left',0,.999,cfg,'walk');self.assertLess(b['target'][0],a['target'][0])
 def test_fixed_bones_and_loop(self):
  r,l=self.rig();r['preserveReach']=True
  for action in ('walk','dash'):
   for i in range(48):
    for p in pose(r,action,i/48)[1]:
     self.assertAlmostEqual(math.dist(p['hip'],p['knee']),p['lengths'][0]);self.assertAlmostEqual(math.dist(p['knee'],p['ankle']),p['lengths'][1])
   self.assertEqual(render(r,l,action,0)[0].tobytes(),render(r,l,action,1)[0].tobytes())
 def test_bad_profile_or_marker(self):
  r,_=self.rig();r['gaitProfile']='unknown'
  with self.assertRaises(ValueError):validate(r)
  r,_=self.rig();r['parts']['left_foot']['heelContact']=[999,0]
  with self.assertRaises(ValueError):validate(r)

 def test_sole_envelope_support_and_flight(self):
  from motion import rotate,sub
  r,_=self.rig()
  for side in ('left','right'):
   p=r['parts'][side+'_foot'];x,y=p['start'];p['soleOutline']=[[x-5,y+3],[x+17,y+4],[x+16,y+8],[x-4,y+7]]
  validate(r)
  for action in ('walk','dash'):
   cfg=gait_config(r,action)
   for i in range(240):
    path=foot_path(r,'left',0,i/240,cfg,action);p=r['parts']['left_foot'];bottom=max(v[1] for v in p['soleOutline']);moved=max(path['target'][1]+rotate(sub(v,p['start']),path['roll'])[1] for v in p['soleOutline'])
    self.assertLessEqual(moved,bottom+1e-9)
    if path['contact']:self.assertAlmostEqual(moved,bottom)
    elif path['phase']>cfg['stance']:self.assertLess(moved,bottom)
