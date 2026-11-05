import unittest,tempfile,json,hashlib
from pathlib import Path
from PIL import Image
import character_workflow as cw

class CharacterTransitionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);inputs={}
  for i,v in enumerate(cw.VIEWS):
   q=self.root/(v+'.png');Image.new('RGBA',(20,30),(i*50,20,90,255)).save(q);inputs[v]=q
  self.profile=cw.init_workspace(inputs,self.root/'work');p=cw.load(self.profile);p.update(identity={'descriptors':['synthetic geometric original']},proportions={'notes':'source geometric proportions'},clothing=[{'name':'long garment','boundary':'source lower hem','length':'original ankle length'}],accessories=[],contacts={'armMode':'free','held':[]},timing={'durationsMs':[200,300,200,300],'phases':['contact','passing','contact','passing']})
  for v in cw.VIEWS:p['views'][v].update(facing='left' if v=='side' else v,representation='coherent-full-cel',ownership={'basis':'near-far' if v=='side' else 'anatomical-left-right','ownerA':'near' if v=='side' else 'left','ownerB':'far' if v=='side' else 'right'})
  cw.dump(self.profile,p);e=self.root/'evidence.txt';e.write_text('Synthetic human intake fixture.');cw.record_intake(self.profile,e,'Synthetic character identity and all view decisions inspected.')
  self.first=self.root/'first.png';self.last=self.root/'last.png';Image.new('RGBA',(24,32),(100,20,50,255)).save(self.first);Image.new('RGBA',(24,32),(50,20,100,255)).save(self.last)
 def tearDown(self):self.tmp.cleanup()
 def request(self,**kwargs):
  args=dict(profile=self.profile,view='side',from_index=1,to_index=2,from_cel=self.first,to_cel=self.last,fractions=[.25,.75]);args.update(kwargs);return cw.plan_transition(**args)
 def annotations(self,frames):
  q=self.root/'landmarks.json';cw.dump(q,{'schema':'character-landmarks/1','view':'side','coordinateSpace':'manual common cel pixels','frames':frames});return q
 def test_actual_endpoints_original_identity_owners_and_ratio(self):
  r=self.request();q=r['requests'][0];self.assertEqual(len(q['actualImageReferences']),3);self.assertEqual(q['endpoints'][0]['supportOwner'],'near');self.assertEqual(q['endpoints'][1]['supportOwner'],'far');self.assertEqual(q['timeFraction'],.25);self.assertEqual(q['elapsedFromStartMs'],75);self.assertEqual(q['intervalDurationMs'],300);self.assertEqual(q['physicalLegOwners'],['near','far']);self.assertEqual(q['contacts']['armMode'],'free');self.assertEqual(q['clothing'][0]['length'],'original ankle length');self.assertIsNone(q['providerToolArguments'])
  for endpoint in q['endpoints']:self.assertEqual(hashlib.sha256((self.profile.parent/endpoint['path']).read_bytes()).hexdigest(),endpoint['sha256'])
 def test_profile_and_bindings_unchanged(self):
  before=self.profile.read_bytes();m=cw.manifest_path(self.profile).read_bytes();self.request();self.assertEqual(before,self.profile.read_bytes());self.assertEqual(m,cw.manifest_path(self.profile).read_bytes())
 def test_wrap_elapsed_and_roles(self):
  r=self.request(from_index=3,to_index=1);self.assertTrue(r['interval']['wrapsLoop']);self.assertEqual(r['interval']['durationMs'],500);self.assertEqual(r['interval']['crossedIndices'],[3,0])
 def test_missing_actual_cel_rejected(self):
  with self.assertRaises(OSError):self.request(from_cel=self.root/'missing.png')
 def test_mismatched_canvas_rejected(self):
  Image.new('RGBA',(12,12),'blue').save(self.last)
  with self.assertRaisesRegex(ValueError,'canvas'):self.request()
 def test_endpoint_index_rejected(self):
  with self.assertRaisesRegex(ValueError,'endpoint indices'):self.request(from_index=1,to_index=1)
 def test_fraction_invalid_rejected(self):
  for value in ([0],[1],[.8,.2],[.2,.2],[float('nan')]):
   with self.assertRaisesRegex(ValueError,'Fractions'):self.request(fractions=value)
 def test_no_request_overwrite(self):
  self.request()
  with self.assertRaisesRegex(ValueError,'new request'):self.request()
 def test_output_confined(self):
  with self.assertRaisesRegex(ValueError,'inside'):self.request(out=self.root/'external.json')
 def test_held_override_is_bound(self):
  p=cw.load(self.profile);p['views']['side']['contacts']={'armMode':'held','held':['original tool grip']};cw.dump(self.profile,p);cw.record_intake(self.profile,self.root/'evidence.txt','Updated held contact seen in original side image.');q=self.request()['requests'][0];self.assertEqual(q['contacts']['held'],['original tool grip'])
 def test_landmarks_known_delta_unknown_unrecorded(self):
  a=self.annotations([{'celIndex':0,'feet':{'near':[10,20]},'pelvis':[10,10],'faceBox':[4,2,8,6]},{'celIndex':1,'feet':{'near':[6,20]},'pelvis':[10,11],'faceBox':[4,3,8,7]}]);r=cw.landmark_report(self.profile,'side',a);d=r['intervals'][0]['samePhysicalSupportFoot'];self.assertEqual(d['dx'],-4);self.assertEqual(d['pixelsPerSecond'],20);self.assertEqual(r['intervals'][1]['samePhysicalSupportFoot']['status'],'unknown');self.assertEqual(r['timeline'][2]['pelvis'],'unknown');self.assertEqual(r['intervals'][0]['faceBox']['centerDelta'],[0,1]);self.assertIn('unknown',r['naturalness'])
 def test_landmarks_owner_must_be_physical_declared(self):
  a=self.annotations([{'celIndex':0,'feet':{'invented':[1,2]}}])
  with self.assertRaisesRegex(ValueError,'physical owner'):cw.landmark_report(self.profile,'side',a)
 def test_landmarks_no_naturalness_pass_from_zeros(self):
  a=self.annotations([{'celIndex':i,'feet':{'near':[1,2],'far':[3,2]},'pelvis':[2,1],'faceBox':[0,0,1,1]} for i in range(4)]);r=cw.landmark_report(self.profile,'side',a);self.assertNotIn('passed',r);self.assertIn('no automatic',r['naturalness'])
 def test_intake_change_blocks_transition(self):
  p=cw.load(self.profile);p['proportions']['notes']='changed';cw.dump(self.profile,p)
  with self.assertRaisesRegex(ValueError,'stale'):self.request()
 def test_transition_constraints_explicit(self):
  q=self.request()['requests'][0];t=' '.join(q['invariants']);self.assertIn('BOTH actual endpoint',t);self.assertIn('do not interpolate the redesign',t);self.assertIn('free arms may swing',t);self.assertIn('Do not normalize',t);self.assertIn('continuous support-foot',q['motionIntent'])

if __name__=='__main__':unittest.main()
