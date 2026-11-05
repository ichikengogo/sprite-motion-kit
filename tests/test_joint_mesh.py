import unittest,math,copy
from PIL import ImageChops
from demo import demo
from motion import render,render_neutral,pose,validate,angle,sub,rotate,add
class JointMeshTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(gaitProfile='coupled-v2',motionScale=.45,preserveReach=True,jointMeshes=[dict(parent=s+'_'+a,child=s+'_'+b,radius=10) for s in ('left','right') for a,b in [('upper_arm','forearm'),('thigh','shin')]])
  return r,l
 def test_neutral_mesh_preserves_source(self):
  r,l=self.fixture();a=render_neutral(r,l);r.pop('jointMeshes');b=render_neutral(r,l)
  # Bilinear triangle sampling at identity may round channels by1, not change geometry.
  self.assertEqual(a.getchannel('A').point(lambda a:255 if a>128 else 0).tobytes(),b.getchannel('A').point(lambda a:255 if a>128 else 0).tobytes())
 def test_bones_and_coupled_wrist(self):
  r,l=self.fixture()
  for action in ('walk','dash'):
   for i in range(48):
    trans,ds=pose(r,action,i/48)
    for side in ('left','right'):
     for name in ('upper_arm','forearm','thigh','shin'):
      part=r['parts'][side+'_'+name];start,theta=trans[side+'_'+name];end=add(start,rotate([math.dist(part['start'],part['end']),0],theta));self.assertTrue(all(math.isfinite(x) for x in end))
     a=r['parts'][side+'_upper_arm'];b=r['parts'][side+'_forearm'];self.assertAlmostEqual(math.dist(trans[side+'_upper_arm'][0],trans[side+'_forearm'][0]),math.dist(a['start'],a['end']))
   self.assertEqual(render(r,l,action,0)[0].tobytes(),render(r,l,action,1)[0].tobytes())
 def test_invalid_mesh(self):
  r,l=self.fixture();r['jointMeshes'][0]['child']='head'
  with self.assertRaises(ValueError):validate(r)
  r,l=self.fixture();r['jointMeshes'][0]['radius']=float('nan')
  with self.assertRaises(ValueError):validate(r)
 def test_actual_wrist_coupling_and_scale(self):
  r,l=self.fixture();r['facing']='left'
  for side in ('left','right'):
   signals=[];wrists=[]
   for i in range(24):
    _,ds=pose(r,'dash',i/24);d=next(d for d in ds if d['side']==side)
    signals.append(d['couplingSignal']);wrists.append(-(d['wrist'][0]-d['shoulder'][0]));self.assertLess(d['armReachErrorPx'],1e-6)
   mean_s=sum(signals)/24;mean_w=sum(wrists)/24;self.assertLess(sum((s-mean_s)*(w-mean_w) for s,w in zip(signals,wrists)),0)
  r['armSwingScale']=0;_,a=pose(r,'dash',0);r['armSwingScale']=1;_,b=pose(r,'dash',0)
  self.assertGreater(abs(a[0]['wrist'][0]-b[0]['wrist'][0]),1)

 def test_no_hard_coupling_plateau(self):
  r,l=self.fixture();r['facing']='left';values=[pose(r,'dash',i/24)[1][1]['couplingSignal'] for i in range(8,13)]
  self.assertGreater(max(values)-min(values),.01)
 def test_waist_attachment_neutral_and_loop(self):
  r,l=self.fixture();old=render_neutral(r,l);r['waistAttachment']={'startFraction':.1,'endFraction':.95};validate(r);new=render_neutral(r,l)
  self.assertEqual(old.getchannel('A').point(lambda a:255 if a>128 else 0).tobytes(),new.getchannel('A').point(lambda a:255 if a>128 else 0).tobytes())
  for action in ('walk','dash'):self.assertEqual(render(r,l,action,0)[0].tobytes(),render(r,l,action,1)[0].tobytes())
 def test_invalid_waist_attachment(self):
  r,l=self.fixture()
  for value in [True,{'startFraction':.9,'endFraction':.2},{'startFraction':0,'endFraction':float('nan')}]:
   r['waistAttachment']=value
   with self.assertRaises(ValueError):validate(r)
  r['waistAttachment']={'startFraction':.1,'endFraction':.95};r['jointMeshes']=[]
  with self.assertRaises(ValueError):validate(r)
