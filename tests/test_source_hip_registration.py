import copy,hashlib,math,unittest
from demo import demo
from motion import angle,foot_path,gait_config,length,pose,render,rotate,sub,validate

class SourceHipRegistrationTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',walkPosture='upright',motionScale=.4)
  return r,l
 def test_source_hips_keep_registered_offset_from_torso(self):
  r,l=self.fixture();r['walkHipRegistration']='source';validate(r);before=copy.deepcopy(r)
  for i in range(24):
   transforms,diag=pose(r,'walk',i/24);torso=r['parts']['torso'];dest,theta=transforms['torso'];delta=theta-angle(sub(torso['end'],torso['start']))
   for side in ('left','right'):
    original=r['parts'][side+'_thigh']['start'];offset=rotate(sub(original,torso['start']),delta);expected=[dest[j]+offset[j] for j in range(2)]
    for actual,want in zip(transforms[side+'_thigh'][0],expected):self.assertAlmostEqual(actual,want,places=10)
    d=next(x for x in diag if x['side']==side)
    source_lengths=[length(sub(r['parts'][side+'_'+p]['end'],r['parts'][side+'_'+p]['start'])) for p in ('thigh','shin')]
    self.assertEqual(d['lengths'],source_lengths)
  self.assertEqual(r,before)
 def test_legacy_raster_prechange_and_foot_paths_unchanged(self):
  expected=['436abc7095ab80f16afcdb30e58415d341b79099c754beb6913e1fc60ddec0cc','95dbe26357a9de5467aadd7018cc58a56cd7a1b32dbbbf7464b4aabca9ace1ec','37f0e883bd7d57fb80acfcf23fee7b31ec831459f47d447b488525cbee1984ad','7d5b8a38eb38e8feeda4c4e481b36574b9ade55d59eea49ca3b4a8240883ff5b']
  r,l=self.fixture();q=copy.deepcopy(r);q['walkHipRegistration']='source';explicit=copy.deepcopy(r);explicit['walkHipRegistration']='legacy-centered'
  for t,h in zip((0,.25,.5,.75),expected):
   self.assertEqual(hashlib.sha256(render(r,l,'walk',t)[0].tobytes()).hexdigest(),h)
   self.assertEqual(pose(r,'walk',t),pose(explicit,'walk',t));self.assertEqual(pose(r,'dash',t),pose(q,'dash',t))
  for i in range(24):
   for j,s in enumerate(('left','right')):self.assertEqual(foot_path(r,s,j,i/24,gait_config(r,'walk'),'walk'),foot_path(q,s,j,i/24,gait_config(q,'walk'),'walk'))
 def test_validation(self):
  for view,style in [('front','simple'),('back','simple'),('side','cautious')]:
   _,r,_=demo(view);r.update(walkHipRegistration='source',walkStyle=style)
   with self.assertRaisesRegex(ValueError,'side simple'):validate(r)
  r,l=self.fixture()
  for value in (False,None,'centered',''):
   r['walkHipRegistration']=value
   with self.assertRaisesRegex(ValueError,'Unknown walkHipRegistration'):validate(r)
