import unittest,tempfile,json,copy,hashlib
from unittest.mock import patch
from pathlib import Path
from PIL import Image,ImageDraw
from drawn_cel import validate,pin_sources,render_frames,export_project,record_review,reviews_status,write_template,GATES,reviews_report

class DrawnCelTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'project.json'
  Image.new('RGBA',(12,10),(0,0,0,0)).save(self.root/'upper.png');Image.new('RGBA',(12,10),'pink').save(self.root/'original.png')
  for i in range(4):
   im=Image.new('RGBA',(12,10));ImageDraw.Draw(im).rectangle((i,3,i+3,9),fill=(40+i*30,40,40,255));im.save(self.root/f'{i}.png')
  self.p={'schema':'drawn-cel-loop/1','canvas':[16,16],'frames':4,'durationSeconds':1,'durationsMs':[250]*4,'identitySources':['original.png'],'upperCel':'upper.png','upperTranslationX':0,'upperAnchorY':0,'registration':[{'source':f'{i}.png','sourceWaist':[0,3],'uniformLowerScale':1,'translation':[0,0],'targetWaist':[0,0]} for i in range(4)],'phaseMetadata':[{'phase':'contact' if i%2==0 else 'passing','supportOwner':'near' if i<2 else 'far','swingOwner':'far' if i<2 else 'near'} for i in range(4)]}
  self.save();pin_sources(self.path);self.p=json.loads(self.path.read_text());self.evidence=self.root/'evidence.txt';self.evidence.write_text('Synthetic fixture observations, not artwork quality approval.')
 def tearDown(self):self.tmp.cleanup()
 def save(self):self.path.write_text(json.dumps(self.p))
 def test_actual_source_dimensions(self):
  frames=render_frames(self.path);self.assertEqual(frames[0].getbbox(),(0,3,4,10))
 def test_pin_staleness(self):
  Image.new('RGBA',(12,10),'red').save(self.root/'0.png')
  with self.assertRaisesRegex(ValueError,'pin'):validate(self.path)
 def test_owner_alternation(self):
  for r in self.p['phaseMetadata']:r.update(supportOwner='near',swingOwner='far')
  self.save()
  with self.assertRaisesRegex(ValueError,'alternates'):validate(self.path)
 def test_raster_repeated_half_detected_despite_claimed_owners(self):
  self.p['registration'][2]['source']='0.png';self.p['registration'][3]['source']='1.png';self.save();pin_sources(self.path)
  with self.assertRaisesRegex(ValueError,'Repeated'):render_frames(self.path)
 def test_traversal_rejected(self):
  self.p['registration'][0]['source']='../outside.png';self.save()
  with self.assertRaisesRegex(ValueError,'escapes'):pin_sources(self.path)
 def test_absolute_rejected(self):
  self.p['registration'][0]['source']=str(self.root/'0.png');self.save()
  with self.assertRaisesRegex(ValueError,'relative'):pin_sources(self.path)
 def test_gif_timing_validation(self):
  self.p['durationsMs'][0]=251;self.save()
  with self.assertRaisesRegex(ValueError,'GIF'):validate(self.path)
 def test_count_validation(self):
  self.p['frames']=5;self.save()
  with self.assertRaisesRegex(ValueError,'count'):validate(self.path)
 def test_semantic_gate_not_inferred_from_opaque_pixels(self):
  with self.assertRaisesRegex(ValueError,'human review'):export_project(self.path,self.root/'reviewed','reviewed-draft')
  report=export_project(self.path,self.root/'draft');self.assertFalse(any(report['humanGates'].values()));self.assertIn('skin versus fabric',report['notAutomaticallyVerified'])
 def continuous_fixture(self):
  if not (self.root/'playback').exists():export_project(self.path,self.root/'playback')
  return {'method':'continuous-playback','reviewer':'test fixture assertion, not an actual artistic reviewer','playbackSpeed':1.0,'methodTool':'synthetic unit-test assertion, not actual viewing','continuityFindings':'Synthetic schema fixture only, no artistic findings.','observations':[{'artifact':str(self.root/'playback'/f'preview-{name}.gif'),'display':name,'loopObserved':True,'completeLoopsObserved':2} for name in ['native','128']]}
 def test_all_gates_and_freshness(self):
  observation=self.continuous_fixture()
  for gate in GATES:record_review(self.path,gate,self.evidence,'Synthetic fixture checked, not artistic approval.',observation)
  self.assertTrue(all(reviews_status(self.path).values()));export_project(self.path,self.root/'reviewed','reviewed-draft')
  self.p['registration'][0]['translation']=[1,0];self.save();self.assertFalse(any(reviews_status(self.path).values()))
 def test_review_evidence_tamper(self):
  row=record_review(self.path,'identity',self.evidence,'Synthetic identity source checked.')
  (self.root/row['evidence']).write_text('changed');self.assertFalse(reviews_status(self.path)['identity'])
 def test_export_no_overwrite(self):
  with self.assertRaisesRegex(ValueError,'new output'):export_project(self.path,self.root)
 def test_source_overlap_restore_preserves_lower_and_upper(self):
  # Existing source material above horizontal crop is restored, not new RGB painting.
  im=Image.open(self.root/'0.png');ImageDraw.Draw(im).rectangle((0,1,3,2),fill=(12,13,14,255));im.save(self.root/'0.png');pin_sources(self.path)
  before=render_frames(self.path)[0];self.p=json.loads(self.path.read_text());self.p['connectionRestorePolygons']={'0':[[0,1],[3,1],[3,3],[0,3]]};self.save();after=render_frames(self.path)[0]
  self.assertEqual(before.crop((0,3,16,16)).tobytes(),after.crop((0,3,16,16)).tobytes());self.assertEqual(after.getpixel((1,1)),(12,13,14,255))
 def test_template_explicitly_incomplete(self):
  result=write_template(self.root/'template.json');self.assertFalse(result['runnable'])
  with self.assertRaises(ValueError):validate(self.root/'template.json')
 def test_nan_scale_rejected(self):
  self.p['registration'][0]['uniformLowerScale']=float('nan');self.save()
  with self.assertRaisesRegex(ValueError,'Scale'):validate(self.path)
 def test_waist_hole_probe_detected(self):
  self.p['coverageProbes']=[{'frame':0,'points':[[10,1]],'minAlpha':255}];self.save()
  with self.assertRaisesRegex(ValueError,'alpha probe failed'):render_frames(self.path)
 def test_opaque_skin_not_semantic_cloth_success(self):
  self.p['coverageProbes']=[{'frame':0,'points':[[1,4]],'minAlpha':255}];self.save();render_frames(self.path)
  for gate in GATES:
   if gate!='cloth_coverage':record_review(self.path,gate,self.evidence,'Synthetic fixture observations only.')
  with self.assertRaisesRegex(ValueError,'cloth_coverage'):export_project(self.path,self.root/'cloth','reviewed-draft')
 def test_horizontal_waist_cut_requires_visual_gate(self):
  for gate in GATES:
   if gate!='waist_connection':record_review(self.path,gate,self.evidence,'Synthetic fixture observations only.')
  with self.assertRaisesRegex(ValueError,'waist_connection'):export_project(self.path,self.root/'waist','reviewed-draft')
 def test_shared_upper_not_identity_appearance_certification(self):
  for gate in GATES:
   if gate!='identity_stability':record_review(self.path,gate,self.evidence,'Synthetic fixture observations only.')
  with self.assertRaisesRegex(ValueError,'identity_stability'):export_project(self.path,self.root/'identity','reviewed-draft')
 def test_legacy_character_specific_clip_requires_migration(self):
  self.p['registration'][0]['clipOldRightHem']=True;self.save()
  with self.assertRaisesRegex(ValueError,'Migrate'):validate(self.path)
 def test_tiny_scale_rejected(self):
  self.p['registration'][0]['uniformLowerScale']=0.00001;self.save()
  with self.assertRaisesRegex(ValueError,'zero size'):validate(self.path)
 def test_bool_frames_rejected(self):
  self.p['frames']=True;self.save()
  with self.assertRaisesRegex(ValueError,'count'):validate(self.path)
 def test_explicit_clip_rectangle(self):
  self.p['registration'][0]['clipRects']=[[0,3,2,5]];self.save();f=render_frames(self.path)[0]
  self.assertEqual(f.getpixel((1,4))[3],0);self.assertEqual(f.getpixel((3,4))[3],255)
 def test_renderer_revision_invalidates_reviews(self):
  record_review(self.path,'identity',self.evidence,'Synthetic identity source checked.')
  self.assertTrue(reviews_status(self.path)['identity'])
  with patch('drawn_cel.renderer_fingerprint',return_value='changed-renderer'):
   self.assertFalse(reviews_status(self.path)['identity'])
 def test_pinned_identity_evidence_reused_and_mutation_invalidates(self):
  row=record_review(self.path,'identity',self.root/'original.png','Synthetic identity source checked.')
  self.assertEqual(row['evidence'],'original.png');self.assertFalse((self.root/'review-evidence').exists())
  Image.new('RGBA',(12,10),'blue').save(self.root/'original.png')
  self.assertFalse(reviews_status(self.path)['identity'])
 def test_unpinned_internal_evidence_archived(self):
  row=record_review(self.path,'identity',self.evidence,'Synthetic identity source checked.')
  self.assertTrue(row['evidence'].startswith('review-evidence/'))
  self.assertEqual((self.root/row['evidence']).read_bytes(),self.evidence.read_bytes())
 def test_sampled_stills_cannot_approve_temporal_gates(self):
  for gate in ['motion_contact','identity_stability']:
   result=record_review(self.path,gate,self.evidence,'Extracted stills and timing inspected only.',{'method':'sampled-stills','reviewer':'fixture','playbackSpeed':1.0,'methodTool':'synthetic unit-test assertion, not actual viewing','continuityFindings':'Synthetic schema fixture only, no artistic findings.','observations':[]})
   self.assertEqual(result['gateStatus']['status'],'unreviewed');self.assertFalse(reviews_status(self.path)[gate])
 def test_legacy_note_cannot_claim_playback(self):
  record_review(self.path,'motion_contact',self.evidence,'Duration and byte equality pass, but playback not viewed.')
  self.assertFalse(reviews_status(self.path)['motion_contact'])
 def test_slow_or_unknown_speed_blocks_temporal_review(self):
  for speed in [.5,None,True]:
   o=self.continuous_fixture();o['playbackSpeed']=speed;r=record_review(self.path,'motion_contact',self.evidence,'Fixture temporal observation metadata.',o)
   self.assertEqual(r['gateStatus']['status'],'blocked')
 def test_missing_tool_count_or_findings_blocks_temporal_review(self):
  for key in ('methodTool','continuityFindings'):
   o=self.continuous_fixture();o.pop(key);r=record_review(self.path,'motion_contact',self.evidence,'Fixture temporal observation metadata.',o);self.assertFalse(r['gateStatus']['valid'])
  o=self.continuous_fixture();o['observations'][0].pop('completeLoopsObserved');r=record_review(self.path,'motion_contact',self.evidence,'Fixture temporal observation metadata.',o);self.assertFalse(r['gateStatus']['valid'])
 def test_missing_view_or_loop_blocks_temporal_review(self):
  o=self.continuous_fixture();o['observations']=o['observations'][:1];r=record_review(self.path,'motion_contact',self.evidence,'Fixture temporal observation metadata.',o);self.assertFalse(r['gateStatus']['valid'])
  o=self.continuous_fixture();o['observations'][1]['loopObserved']=False;r=record_review(self.path,'motion_contact',self.evidence,'Fixture temporal observation metadata.',o);self.assertFalse(r['gateStatus']['valid'])
 def test_still_png_claimed_as_playback_is_blocked(self):
  o=self.continuous_fixture();o['observations'][0]['artifact']=str(self.root/'0.png');r=record_review(self.path,'motion_contact',self.evidence,'Fixture temporal observation metadata.',o);self.assertFalse(r['gateStatus']['valid'])
 def test_playback_artifact_tamper_blocks_gate(self):
  o=self.continuous_fixture();r=record_review(self.path,'motion_contact',self.evidence,'Fixture temporal observation metadata.',o);self.assertTrue(r['gateStatus']['valid']);stored=self.root/r['observation']['observations'][0]['artifact'];stored.write_bytes(b'changed');self.assertFalse(reviews_status(self.path)['motion_contact'])
 def test_other_animation_same_dimensions_timing_is_blocked(self):
  o=self.continuous_fixture();wrong=self.root/'wrong.gif';ims=[Image.new('RGB',(16,16),c) for c in ['red','blue','green','yellow']];ims[0].save(wrong,save_all=True,append_images=ims[1:],duration=[250]*4,loop=0);o['observations'][0]['artifact']=str(wrong);r=record_review(self.path,'motion_contact',self.evidence,'Fixture temporal observation metadata.',o);self.assertFalse(r['gateStatus']['valid'])
 def test_reviewer_required(self):
  o=self.continuous_fixture();o['reviewer']='';r=record_review(self.path,'motion_contact',self.evidence,'Fixture temporal observation metadata.',o);self.assertFalse(r['gateStatus']['valid'])
 def test_duration_export(self):
  export_project(self.path,self.root/'out');g=Image.open(self.root/'out/preview-native.gif');ds=[]
  for i in range(g.n_frames):g.seek(i);ds.append(g.info['duration'])
  self.assertEqual(ds,[250]*4);g.close()

if __name__=='__main__':unittest.main()
