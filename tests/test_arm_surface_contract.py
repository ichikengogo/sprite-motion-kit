"""Arm-intent schema/propagation checks. These are NOT semantic visual validation."""
import copy,json,tempfile,unittest
from pathlib import Path
from PIL import Image
import character_workflow as cw

class ArmSurfaceContractTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);inputs={}
  for i,v in enumerate(cw.VIEWS):
   q=self.root/(v+'.png');Image.new('RGBA',(30+i,50),(60*i,20,40,255)).save(q);inputs[v]=q
  self.profile=cw.init_workspace(inputs,self.root/'work');self.p=cw.load(self.profile);self.initial=copy.deepcopy(self.p)
  self.p.update(identity={'descriptors':['synthetic broad figure']},proportions={'notes':'wide torso with short forearms'},clothing=[{'name':'sleeveless tunic','boundary':'original open armhole','length':'original hem'}],accessories=[],contacts={'armMode':'free','held':[]},timing={'durationsMs':[250]*4,'phases':['contact','passing','contact','passing']})
  for v in cw.VIEWS:self.p['views'][v].update(facing='right' if v=='side' else v,representation='coherent-full-cel',ownership={'basis':'near-far' if v=='side' else 'anatomical-left-right','ownerA':'near' if v=='side' else 'left','ownerB':'far' if v=='side' else 'right'})
  self.e=self.root/'review.txt';self.e.write_text('Synthetic source intake only, not visual arm approval.');self.save()
 def tearDown(self):self.tmp.cleanup()
 def save(self):cw.dump(self.profile,self.p)
 def review(self):self.save();cw.record_intake(self.profile,self.e,'Synthetic fixture identity and declared decisions inspected.')
 def arm(self,identity='left',surface='dorsal',mode='free'):
  return {'physicalArmId':identity,'visibleHandSurface':surface,'mode':mode,'pose':'follow source shoulder with relaxed elbow','contacts':['tool grip shown in source'] if mode=='held' else [],'shoulderBoundary':'bare shoulder inside original tunic armhole','elbowContinuity':'one continuous forearm from this elbow','wristContinuity':'hand remains attached to this wrist','occlusionExpectation':'keep source overlap; hidden surface remains unverified'}
 def spec(self,*arms):return {'arms':list(arms)}
 def test_init_prompts_without_mandatory_palm(self):
  self.assertTrue(all(self.initial['views'][v]['armSurfaceSpec'] is None for v in cw.VIEWS));self.assertIn('unrecorded',self.initial['instructions']);self.assertIn('never an instruction to show palms',self.initial['instructions'])
 def test_legacy_missing_and_null_are_unknown(self):
  del self.p['views']['side']['armSurfaceSpec'];self.review();requests=cw.plan(self.profile)['requests'];self.assertTrue(all(r['armSurfaceReview']['status']=='unrecorded' for r in requests));self.assertTrue(all(r['armSurfaceSpec'] is None for r in requests))
 def test_free_sleeveless_dorsal_and_edge_propagate(self):
  spec=self.spec(self.arm('left','dorsal'),self.arm('right','edge'));self.p['views']['front']['armSurfaceSpec']=spec;self.review();r=cw.plan(self.profile)['requests'][0];self.assertEqual(r['armSurfaceSpec'],spec);self.assertFalse(r['armSurfaceReview']['automaticSemanticValidation']);self.assertEqual(r['armSurfaceReview']['status'],'specified-not-visually-validated')
 def test_held_sleeved_tall_body_is_independent(self):
  self.p['identity']['descriptors']=['synthetic tall figure'];self.p['proportions']['notes']='slender torso and longer arms';self.p['clothing']=[{'name':'long sleeve coat','boundary':'source sleeve cap and cuff','length':'original knee hem'}];self.p['views']['side']['contacts']={'armMode':'held','held':['source tool']};a=self.arm('right','palm','held');a['shoulderBoundary']='source coat sleeve cap joins shoulder without gap';b=self.arm('left','occluded');self.p['views']['side']['armSurfaceSpec']=self.spec(a,b);self.review();r=next(x for x in cw.plan(self.profile)['requests'] if x['view']=='side');self.assertEqual(r['armSurfaceSpec']['arms'][0]['mode'],'held');self.assertEqual(r['armSurfaceSpec']['arms'][1]['visibleHandSurface'],'occluded');self.assertEqual(r['proportions'],self.p['proportions'])
 def test_none_can_have_no_arm_descriptions(self):
  self.p['views']['back']['contacts']={'armMode':'none','held':[]};self.p['views']['back']['armSurfaceSpec']={'arms':[]};self.review();r=next(x for x in cw.plan(self.profile)['requests'] if x['view']=='back');self.assertEqual(r['armSurfaceSpec']['arms'],[])
 def test_source_dependent_not_silently_palm(self):
  self.p['views']['side']['armSurfaceSpec']=self.spec(self.arm('physical-A','source-dependent'));self.review();r=next(x for x in cw.plan(self.profile)['requests'] if x['view']=='side');self.assertEqual(r['armSurfaceSpec']['arms'][0]['visibleHandSurface'],'source-dependent')
 def test_transition_propagates_exact_surface_and_attachment(self):
  spec=self.spec(self.arm('physical-A','edge'),self.arm('physical-B','dorsal'));self.p['views']['side']['armSurfaceSpec']=spec;self.review();a=self.root/'a.png';b=self.root/'b.png';Image.new('RGBA',(30,50),'red').save(a);Image.new('RGBA',(30,50),'blue').save(b);r=cw.plan_transition(self.profile,'side',1,2,a,b,[.5]);self.assertEqual(r['requests'][0]['armSurfaceSpec'],spec);self.assertFalse(r['requests'][0]['armSurfaceReview']['automaticSemanticValidation'])
 def test_invalid_surface_rejected(self):
  self.p['views']['side']['armSurfaceSpec']=self.spec(self.arm(surface='always-palm'));self.save()
  with self.assertRaisesRegex(ValueError,'visibleHandSurface'):cw.decisions(self.profile)
 def test_duplicate_physical_identity_rejected(self):
  self.p['views']['side']['armSurfaceSpec']=self.spec(self.arm('left'),self.arm('left'));self.save()
  with self.assertRaisesRegex(ValueError,'Duplicate physicalArmId'):cw.decisions(self.profile)
 def test_missing_joint_contract_rejected(self):
  a=self.arm();del a['wristContinuity'];self.p['views']['side']['armSurfaceSpec']=self.spec(a);self.save()
  with self.assertRaisesRegex(ValueError,'fields'):cw.decisions(self.profile)
 def test_coordinates_instead_of_source_boundary_rejected(self):
  a=self.arm();a['shoulderBoundary']=[12,15];self.p['views']['side']['armSurfaceSpec']=self.spec(a);self.save()
  with self.assertRaisesRegex(ValueError,'shoulderBoundary'):cw.decisions(self.profile)
 def test_held_contacts_cannot_be_empty(self):
  a=self.arm(mode='held');a['contacts']=[];self.p['views']['side']['armSurfaceSpec']=self.spec(a);self.save()
  with self.assertRaisesRegex(ValueError,'Held arm'):cw.decisions(self.profile)
 def test_free_overall_cannot_silently_hold(self):
  self.p['views']['side']['armSurfaceSpec']=self.spec(self.arm(mode='held'));self.save()
  with self.assertRaisesRegex(ValueError,'contradict'):cw.decisions(self.profile)
 def test_empty_free_spec_is_not_completed_decision(self):
  self.p['views']['side']['armSurfaceSpec']={'arms':[]};self.save()
  with self.assertRaisesRegex(ValueError,'describe physical arms'):cw.decisions(self.profile)
 def test_free_overall_rejects_all_none_arm_records(self):
  self.p['views']['side']['armSurfaceSpec']=self.spec(self.arm('left',mode='none'),self.arm('right',mode='none'));self.save()
  with self.assertRaisesRegex(ValueError,'contradict'):cw.decisions(self.profile)
 def test_free_overall_accepts_free_and_none_mixture(self):
  spec=self.spec(self.arm('left',mode='free'),self.arm('right',mode='none'));self.p['views']['side']['armSurfaceSpec']=spec;self.review();r=next(x for x in cw.plan(self.profile)['requests'] if x['view']=='side');self.assertEqual(r['armSurfaceSpec'],spec)
 def test_contract_change_invalidates_intake(self):
  self.review();self.p['views']['front']['armSurfaceSpec']=self.spec(self.arm());self.save()
  with self.assertRaisesRegex(ValueError,'stale'):cw.plan(self.profile)

if __name__=='__main__':unittest.main()
