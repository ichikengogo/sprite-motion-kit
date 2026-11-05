import copy, importlib.util, math, unittest
from pathlib import Path
from demo import demo
from motion import angle, foot_path, gait_config, length, pose, render, rotate, sub, validate

class HipDriveTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',walkPosture='upright',motionScale=.4,walkHipRegistration='source',legSwing='thigh-led',legRecovery='clear-step',armPose='held-source')
  return r,l
 def driven(self,r):
  q=copy.deepcopy(r);q['walkHipDrive']={'confirmed':True,'pelvisShift':4,'pelvisTilt':.06,'torsoCounter':.02,'swingLead':.25};return q
 def test_lengths_stance_targets_and_held_arms(self):
  r,l=self.fixture();q=self.driven(r);validate(q);before=copy.deepcopy(q)
  for i in range(48):
   t=i/48;tr,ds=pose(q,'walk',t);torso=q['parts']['torso'];dst,theta=tr['torso'];ta=theta-angle(sub(torso['end'],torso['start']))
   for j,d in enumerate(ds):
    side=d['side'];self.assertAlmostEqual(length(sub(d['knee'],d['hip'])),d['lengths'][0],places=9);self.assertAlmostEqual(length(sub(d['ankle'],d['knee'])),d['lengths'][1],places=9)
    raw=foot_path(r,side,j,t,gait_config(r,'walk'),'walk')
    if d['contact']:
     self.assertLess(length(sub(d['ankle'],raw['target'])),1e-4);self.assertEqual(d['hipSwingLeadRadians'],0)
    for name in (side+'_upper_arm',side+'_forearm'):
     part=q['parts'][name];offset=rotate(sub(part['start'],torso['start']),ta)
     for a,b in zip(tr[name][0],[dst[k]+offset[k] for k in range(2)]):self.assertAlmostEqual(a,b,places=10)
     self.assertAlmostEqual(tr[name][1]-angle(sub(part['end'],part['start'])),ta,places=10)
  self.assertEqual(q,before)
 def test_swing_rotates_whole_leg_not_only_shin(self):
  r,l=self.fixture();q=self.driven(r);q['walkHipDrive'].update(pelvisShift=0,pelvisTilt=0,torsoCounter=0)
  for facing,direction in [('right',1),('left',-1)]:
   r['facing']=q['facing']=facing
   for t in (.65,.7,.8,.9,.95):
    a,ad=pose(r,'walk',t);b,bd=pose(q,'walk',t);d0=ad[0];d1=bd[0];lead=-direction*.25*math.sin(math.pi*((t-.6)/.4))**2
    for key in ('knee','ankle'):
     expected=rotate(sub(d0[key],d0['hip']),lead)
     for actual,want in zip(sub(d1[key],d1['hip']),expected):self.assertAlmostEqual(actual,want,places=9)
    self.assertAlmostEqual(d1['hipSwingLeadRadians'],lead,places=10)
   for t in (0,.125,.5):self.assertEqual(pose(r,'walk',t)[0]['left_foot'],pose(q,'walk',t)[0]['left_foot'])
 def test_zero_drive_and_dash_preserve_default_raster(self):
  r,l=self.fixture();q=self.driven(r)
  for k in ('pelvisShift','pelvisTilt','torsoCounter','swingLead'):q['walkHipDrive'][k]=0
  for t in (0,.125,.25,.75):
   self.assertEqual(pose(r,'walk',t)[0],pose(q,'walk',t)[0]);self.assertEqual(render(r,l,'walk',t)[0].tobytes(),render(q,l,'walk',t)[0].tobytes())
   self.assertEqual(pose(r,'dash',t),pose(self.driven(r),'dash',t))
 def test_phase_continuity_and_pelvis_body_relation(self):
  r,l=self.fixture();q=self.driven(r)
  for t in (0,.1,.25,.45,.6,.8,.999):
   tr,ds=pose(q,'walk',t)
   for d in ds:
    direction=1
    self.assertAlmostEqual(d['pelvisLeanRadians']-.025,direction*.06*math.sin(2*math.pi*t),places=10)
    self.assertAlmostEqual(d['torsoLeanRadians']-.025,-direction*.02*math.sin(2*math.pi*t),places=10)
  a,_=pose(q,'walk',0);b,_=pose(q,'walk',1)
  self.assertEqual(a,b)
  for boundary in (.6,1):
   # Added lead vanishes with a zero first derivative at both swing endpoints.
   epsilon=1e-5
   value=.25*math.sin(math.pi*((boundary-epsilon-.6)/.4))**2
   self.assertLess(value/epsilon,.001)
 def test_source_ankle_centers_preserve_projection_stride_and_cycle(self):
  r,l=self.fixture();q=self.driven(r);q['walkHipDrive']['gaitCenter']='source-ankles';validate(q);before=copy.deepcopy(q)
  center=sum(r['parts'][side+'_shin']['end'][0] for side in ('left','right'))/2
  for i in range(48):
   t=i/48;tr,ds=pose(q,'walk',t)
   for index,d in enumerate(ds):
    side=d['side'];raw=foot_path(q,side,index,t,gait_config(q,'walk'),'walk');old=foot_path(r,side,index,t,gait_config(r,'walk'),'walk')
    self.assertAlmostEqual(raw['target'][0]-old['target'][0],r['parts'][side+'_shin']['end'][0]-center,places=10)
    self.assertEqual(raw['ground_velocity'],old['ground_velocity']);self.assertEqual(raw['target'][1],old['target'][1])
    if d['contact']:self.assertLess(length(sub(d['ankle'],raw['target'])),1e-4)
    self.assertAlmostEqual(length(sub(d['knee'],d['hip'])),d['lengths'][0],places=9)
    self.assertAlmostEqual(length(sub(d['ankle'],d['knee'])),d['lengths'][1],places=9)
  self.assertEqual(q,before);self.assertEqual(pose(q,'walk',0),pose(q,'walk',1));self.assertEqual(pose(q,'dash',.3),pose(r,'dash',.3))
  for value in ('unknown',None,False,1):
   bad=copy.deepcopy(q);bad['walkHipDrive']['gaitCenter']=value
   with self.assertRaises(ValueError):validate(bad)
 def test_validation(self):
  r,l=self.fixture();q=self.driven(r)
  for key,value in [('confirmed',False),('pelvisShift',9),('pelvisTilt',.121),('torsoCounter',.051),('swingLead',.351),('swingLead',float('nan')),('pelvisShift',True)]:
   bad=copy.deepcopy(q);bad['walkHipDrive'][key]=value
   with self.assertRaises(ValueError):validate(bad)
  for key,value in [('view','front'),('walkStyle','cautious'),('walkHipRegistration','legacy-centered')]:
   bad=copy.deepcopy(q);bad[key]=value
   with self.assertRaises(ValueError):validate(bad)
  bad=copy.deepcopy(q);bad['walkHipDrive']['extra']=1
  with self.assertRaises(ValueError):validate(bad)
