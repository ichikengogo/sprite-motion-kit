"""Geometry-only multi-profile acceptance. Not aesthetic/gait certification."""
import json,tempfile,unittest
from pathlib import Path
from PIL import Image
import synthetic_profiles as fixtures
import drawn_cel

class SyntheticProfileTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_two_profiles_three_views_nonfixed_contract(self):
  specs=fixtures.build_assets(self.root/'assets')
  self.assertEqual({tuple(x['spec']['canvas']) for x in specs.values()},{(192,288),(256,224)})
  self.assertEqual({x['spec']['frames'] for x in specs.values()},{8,10})
  for item in specs.values():
   self.assertEqual(set(item['projects']),{'front','side','back'})
   for view,path in item['projects'].items():
    project=drawn_cel.validate(path);frames=drawn_cel.render_frames(path)
    self.assertEqual(len(frames),item['spec']['frames']);self.assertEqual(frames[0].size,tuple(item['spec']['canvas']))
    self.assertNotEqual(frames[0].tobytes(),frames[len(frames)//2].tobytes())
    self.assertEqual(project['legOwners'],['near','far'] if view=='side' else ['anatomical-left','anatomical-right'])
    self.assertFalse(all(drawn_cel.reviews_status(path).values()))
 def test_same_workflow_for_both_profiles_all_views(self):
  specs=fixtures.build_assets(self.root/'assets');reports=fixtures.run_workflows(specs,self.root/'workspaces')
  self.assertEqual(set(reports),set(fixtures.SPECS))
  for name,report in reports.items():
   workspace=Path(report['workspace']);self.assertTrue((workspace/'generation-requests.json').is_file())
   for view in ('front','side','back'):
    exported=json.loads((workspace/'rendered'/view/'export.json').read_text())
    self.assertEqual(exported['frames'],fixtures.SPECS[name]['frames']);self.assertEqual(exported['quality'],'draft')
    self.assertFalse(all(exported['humanGates'].values()))
 def test_fixture_originals_and_appearance_differ(self):
  specs=fixtures.build_assets(self.root/'assets')
  for item in specs.values():
   imgs=[Image.open(Path(item['originals'])/(v+'.png')).tobytes() for v in ('front','side','back')]
   self.assertEqual(len(set(imgs)),3)
  self.assertNotEqual(fixtures.SPECS['tall-tunic']['garment'],fixtures.SPECS['broad-overalls']['garment'])
  self.assertNotEqual(fixtures.SPECS['tall-tunic']['held'],fixtures.SPECS['broad-overalls']['held'])
if __name__=='__main__':unittest.main()
