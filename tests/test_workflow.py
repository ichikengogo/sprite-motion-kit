import unittest,tempfile,json,shutil
from pathlib import Path
from PIL import Image
from demo import demo
from server import image_data
from workflow import init,bind,attest,identity,export_project,preflight,GATES,VIEWS,read,status,gif_durations
class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name);self.inputs={};self.projects={}
  for v in VIEWS:
   im,rig,layers=demo(v);im.save(self.p/(v+'.png'));self.inputs[v]=self.p/(v+'.png')
   self.projects[v]={'rig':rig,'image':image_data(im),'demo':False,'partImages':{k:image_data(im) for k,im in layers.items()}}
  self.j=self.p/'project.json';self.j.write_text(json.dumps({'projects':self.projects}))
  self.e=self.p/'review.txt';self.e.write_text('Synthetic fixture review only, not artistic approval.')
 def tearDown(self):self.t.cleanup()
 def setup_project(self):
  init(self.p/'work',self.inputs);p=self.p/'work/manifest.json'
  identity(p,self.e,'Inspected synthetic input fixture; matching design in three views.')
  bind(p,self.j);return p
 def gates(self,p,views=VIEWS,gates=('source_correspondence','proportions')):
  for v in views:
   for g in gates:attest(p,g,self.e,'Synthetic fixture review only','walk',v)
 def test_intake_immutable(self):
  m=init(self.p/'work',self.inputs);self.assertEqual((self.p/'work/inputs/side.png').read_bytes(),self.inputs['side'].read_bytes());self.assertFalse(m['views']['front']['engine_reference_validated'])
  with self.assertRaises(ValueError):init(self.p/'work',self.inputs)
 def test_invalid_images(self):
  for color in ('red',(0,0,0,0)):
   Image.new('RGBA',(10,10),color).save(self.inputs['side'])
   with self.assertRaises(ValueError):init(self.p/'work',self.inputs)
 def test_duplicate_sources(self):
  with self.assertRaisesRegex(ValueError,'distinct'):init(self.p/'work',{v:self.inputs['side'] for v in VIEWS})
 def test_identity_required_before_bind(self):
  init(self.p/'work',self.inputs)
  with self.assertRaisesRegex(ValueError,'identity'):bind(self.p/'work/manifest.json',self.j)
 def test_source_mismatch_rejected(self):
  p=self.setup_project();self.projects['front']['image']=self.projects['side']['image'];self.j.write_text(json.dumps({'projects':self.projects}))
  with self.assertRaisesRegex(ValueError,'Source mismatch'):bind(p,self.j)
 def test_unchecked_rig_rejected(self):
  p=self.setup_project();self.projects['front']['rig']['confirmed']=False;self.j.write_text(json.dumps({'projects':self.projects}))
  with self.assertRaises(ValueError):bind(p,self.j)
 def test_gates_and_invalidation(self):
  p=self.setup_project()
  with self.assertRaisesRegex(ValueError,'source_correspondence'):preflight(p,'front','walk','draft')
  self.gates(p)
  preflight(p,'front','walk','draft')
  with self.assertRaisesRegex(ValueError,'ownership'):preflight(p,'front','walk','reviewed-draft')
  with self.assertRaises(ValueError):preflight(p,'side','dash','draft')
  (self.p/'work/working-project.json').write_text('{}')
  st=status(p);self.assertFalse(st['integrity']['project_current']);self.assertEqual(st['views']['front']['missing_gates']['walk'],list(GATES))
  with self.assertRaisesRegex(ValueError,'Project changed'):preflight(p,'side','walk','draft')
 def test_changed_input_invalidates(self):
  p=self.setup_project();self.gates(p);(self.p/'work/inputs/front.png').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'Intake source changed'):preflight(p,'side','walk','draft')
 def test_portable_evidence_and_staleness(self):
  p=self.setup_project();self.gates(p);shutil.copytree(self.p/'work',self.p/'moved');shutil.rmtree(self.p/'work');self.e.unlink()
  p=self.p/'moved/manifest.json';preflight(p,'back','walk','draft')
  e=read(p)['views']['front']['review']['walk']['proportions']['evidence'];(p.parent/e).write_text('changed')
  with self.assertRaises(ValueError):preflight(p,'front','walk','draft')
  self.assertIn('proportions',status(p)['views']['front']['missing_gates']['walk'])
 def test_unbound_explains_next_step(self):
  init(self.p/'work',self.inputs)
  with self.assertRaisesRegex(ValueError,'workflow.py bind'):export_project(self.p/'work/manifest.json','side','walk',self.p/'out')
 def test_rebind_clears_review(self):
  p=self.setup_project();self.gates(p);bind(p,self.j);self.assertEqual(read(p)['views']['front']['review'],{})
 def test_gif_timing(self):
  d=gif_durations([i/8 for i in range(8)],1)
  self.assertEqual(sum(d),1000);self.assertEqual(set(d),{120,130})
 def test_all_export_draft_end_to_end(self):
  p=self.setup_project();self.gates(p);out=self.p/'export';export_project(p,'all','walk',out)
  self.assertFalse(read(out/'summary.json')['approved'])
  for name in ('comparison.gif','front/preview.gif','side/preview.gif','back/preview.gif'):
   gif=Image.open(out/name);duration=0
   for i in range(gif.n_frames):gif.seek(i);duration+=gif.info['duration']
   self.assertEqual(duration,1000)
  for v in VIEWS:
   self.assertTrue((out/v/'sheet.png').is_file());self.assertTrue(read(out/v/'review.json')['draft']);self.assertFalse(read(out/v/'review.json')['approved'])
  with self.assertRaises(ValueError):export_project(p,'all','walk',out)
 def test_all_preflight_leaves_no_partial_output(self):
  p=self.setup_project();self.gates(p,('front','side'));out=self.p/'export'
  with self.assertRaises(ValueError):export_project(p,'all','walk',out)
  self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
