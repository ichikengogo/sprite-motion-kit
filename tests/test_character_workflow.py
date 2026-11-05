import unittest,tempfile,json
from pathlib import Path
from PIL import Image,ImageDraw
from unittest.mock import patch
import character_workflow as cw
import drawn_cel as dc

class CharacterWorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);inputs={}
  for i,v in enumerate(cw.VIEWS):
   q=self.root/(v+'.png');Image.new('RGBA',(20,30),(i*50,20,90,255)).save(q);inputs[v]=q
  self.profile=cw.init_workspace(inputs,self.root/'work');self.p=json.loads(self.profile.read_text());self.p.update(identity={'descriptors':['synthetic geometric character']},proportions={'notes':'arbitrary synthetic proportions, no anatomy approval'},clothing=[],accessories=[],contacts={'armMode':'free','held':[]},timing={'durationsMs':[250]*4,'phases':['contact','passing','contact','passing']})
  for v in cw.VIEWS:self.p['views'][v]={'facing':'left' if v=='side' else v,'representation':'coherent-full-cel','ownership':{'basis':'near-far' if v=='side' else 'anatomical-left-right','ownerA':'near' if v=='side' else 'left','ownerB':'far' if v=='side' else 'right'}}
  self.save();self.evidence=self.root/'evidence.txt';self.evidence.write_text('Synthetic fixture only, not visual certification.');self.review()
 def tearDown(self):self.tmp.cleanup()
 def save(self):self.profile.write_text(json.dumps(self.p))
 def review(self):cw.record_intake(self.profile,self.evidence,'All three synthetic identities and profile decisions inspected.')
 def cells(self,view):
  folder=self.root/('cels-'+view);folder.mkdir()
  for i in range(4):
   im=Image.new('RGBA',(24,32));ImageDraw.Draw(im).rectangle((i+3,3,i+9,29),fill=(80+i*20,10,60,255));im.save(folder/f'{i:02}.png')
  return folder
 def test_init_unknown_not_character_specific(self):
  inputs={v:self.root/(v+'.png') for v in cw.VIEWS};p=cw.init_workspace(inputs,self.root/'unknown');j=json.loads(p.read_text());self.assertIsNone(j['clothing']);self.assertIsNone(j['timing']['durationsMs'])
  with self.assertRaisesRegex(ValueError,'identity'):cw.plan(p)
 def test_plan_three_views_roles_and_provider_independent(self):
  p=cw.plan(self.profile);self.assertEqual(len(p['requests']),12);self.assertIsNone(p['provider']);self.assertEqual(p['requests'][0]['supportOwner'],'left');self.assertEqual(p['requests'][2]['supportOwner'],'right');self.assertNotIn('pixelCoordinates',p['registrationHandoff'])
 def test_profile_change_invalidates_review(self):
  self.p['proportions']['notes']='changed';self.save()
  with self.assertRaisesRegex(ValueError,'stale'):cw.plan(self.profile)
 def test_original_change_rejected(self):
  Image.new('RGBA',(20,30),'red').save(self.profile.parent/'inputs/front.png')
  with self.assertRaisesRegex(ValueError,'source changed'):cw.plan(self.profile)
 def test_no_partial_three_view_success(self):
  with self.assertRaisesRegex(ValueError,'All three'):cw.render_all(self.profile,self.root/'out')
  self.assertFalse((self.root/'out').exists())
 def test_register_count_rejected(self):
  d=self.cells('front');(d/'03.png').unlink()
  with self.assertRaisesRegex(ValueError,'count'):cw.register_cels(self.profile,'front',d)
 def test_register_mixed_canvas_rejected(self):
  d=self.cells('front');Image.new('RGBA',(12,16),'blue').save(d/'03.png')
  with self.assertRaisesRegex(ValueError,'canvas'):cw.register_cels(self.profile,'front',d)
 def test_full_cel_same_entry_three_exports(self):
  for v in cw.VIEWS:cw.register_cels(self.profile,v,self.cells(v))
  report=cw.render_all(self.profile,self.root/'out');self.assertEqual(set(report['views']),set(cw.VIEWS));self.assertTrue((self.root/'out/back/frame-03.png').is_file())
 def test_wrong_original_binding_rejected(self):
  row=cw.register_cels(self.profile,'front',self.cells('front'))
  with self.assertRaisesRegex(ValueError,'identity source'):cw.bind(self.profile,'back',row['project'])
 def test_bound_project_modification_rejected(self):
  for v in cw.VIEWS:cw.register_cels(self.profile,v,self.cells(v))
  q=self.profile.parent/'projects/front/project.json';j=json.loads(q.read_text());j['registration'][0]['translation']=[1,0];q.write_text(json.dumps(j))
  with self.assertRaisesRegex(ValueError,'Stale binding'):cw.render_all(self.profile,self.root/'out')
 def test_external_binding_rejected(self):
  with self.assertRaisesRegex(ValueError,'inside'):cw.bind(self.profile,'front',self.root/'external.json')
 def test_reviewed_draft_requires_each_view_gates(self):
  for v in cw.VIEWS:cw.register_cels(self.profile,v,self.cells(v))
  with self.assertRaisesRegex(ValueError,'review gates'):cw.render_all(self.profile,self.root/'out','reviewed-draft')
 def test_intake_evidence_mutation_rejected(self):
  row=cw.load(cw.intake_path(self.profile));(self.profile.parent/row['evidence']).write_text('changed')
  with self.assertRaisesRegex(ValueError,'stale'):cw.plan(self.profile)
 def test_registered_timing_mismatch_rejected(self):
  row=cw.register_cels(self.profile,'front',self.cells('front'));q=Path(row['project']);j=cw.load(q);j['durationsMs']=[240,260,250,250];cw.dump(q,j)
  with self.assertRaisesRegex(ValueError,'timing'):cw.bind(self.profile,'front',q)
 def test_register_preserves_source_bytes(self):
  d=self.cells('front');row=cw.register_cels(self.profile,'front',d);q=Path(row['project'])
  self.assertEqual((q.parent/'sources/cel-00.png').read_bytes(),(d/'00.png').read_bytes())
  self.assertEqual((q.parent/'sources/original.png').read_bytes(),(self.profile.parent/'inputs/front.png').read_bytes())
 def test_new_outputs_do_not_overwrite(self):
  for v in cw.VIEWS:cw.register_cels(self.profile,v,self.cells(v))
  with self.assertRaisesRegex(ValueError,'New output'):cw.render_all(self.profile,self.profile.parent)
 def test_failed_export_cleans_stage_without_false_completion(self):
  for v in cw.VIEWS:cw.register_cels(self.profile,v,self.cells(v))
  with patch('character_workflow.drawn_cel.export_project',side_effect=ValueError('fixture renderer failed')):
   with self.assertRaisesRegex(ValueError,'renderer failed'):cw.render_all(self.profile,self.root/'failed')
  self.assertFalse((self.root/'failed').exists());self.assertFalse(list(self.root.glob('.character-export-*')))
 def test_plan_actions_view_rules_and_constant_canvas(self):
  r=cw.plan(self.profile)['requests'];self.assertIn('heel contact',r[0]['phaseAction']);self.assertIn('low clearance',r[1]['phaseAction']);self.assertEqual(r[0]['consistentCanvas'],[20,30]);self.assertIsNone(r[0]['providerToolArguments']);self.assertTrue(any('do not invent' in x for x in r[-1]['viewRules']))
 def test_front_near_far_ambiguity_blocked(self):
  self.p['views']['front']['ownership']['basis']='near-far';self.save()
  with self.assertRaisesRegex(ValueError,'anatomical-left-right'):cw.decisions(self.profile)
 def test_neighbor_context_wraps_loop(self):
  r=cw.plan(self.profile)['requests'];self.assertEqual(r[0]['adjacentPoseContext']['previous']['celIndex'],3);self.assertEqual(r[0]['adjacentPoseContext']['previous']['supportOwner'],'right');self.assertEqual(r[3]['adjacentPoseContext']['next']['celIndex'],0);self.assertIn('forward recovery-leg',r[0]['adjacentPoseContext']['instruction'])
 def test_per_view_contact_override_and_occlusion_notes(self):
  self.p['views']['side']['contacts']={'armMode':'held','held':['hands hold the tool shown in this side original']};self.p['views']['side']['occlusionNotes']='Rear forearm partly hidden; do not claim visible source pixels.';self.save();self.review();r=cw.plan(self.profile)['requests'];front=next(x for x in r if x['view']=='front');side=next(x for x in r if x['view']=='side');self.assertEqual(front['contacts']['armMode'],'free');self.assertEqual(side['contacts']['armMode'],'held');self.assertIn('partly hidden',side['occlusionNotes'])
 def test_invalid_per_view_contact_override_rejected(self):
  self.p['views']['side']['contacts']={'armMode':'held','held':[]};self.save()
  with self.assertRaisesRegex(ValueError,'Held arm'):cw.decisions(self.profile)
 def test_null_per_view_contacts_inherit_global(self):
  self.p['views']['front']['contacts']=None;self.save();self.review();r=cw.plan(self.profile)['requests'];self.assertEqual(r[0]['contacts'],self.p['contacts'])
 def test_invalid_occlusion_type_rejected(self):
  self.p['views']['side']['occlusionNotes']=['hidden'];self.save()
  with self.assertRaisesRegex(ValueError,'occlusionNotes'):cw.decisions(self.profile)
 def test_provider_requests_do_not_register_or_generate(self):
  cw.plan(self.profile);self.assertFalse((self.profile.parent/'projects').exists());self.assertEqual(cw.load(cw.manifest_path(self.profile))['bindings'],{})

if __name__=='__main__':unittest.main()
