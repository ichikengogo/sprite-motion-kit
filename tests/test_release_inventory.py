import importlib.util
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('release_check',Path(__file__).parents[1]/'scripts/check_public_release.py')
release_check=importlib.util.module_from_spec(spec);spec.loader.exec_module(release_check)

class ReleaseInventoryTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def test_curated_text_only_and_ignored_outputs(self):
  (self.root/'README.md').write_text('Original source documentation')
  (self.root/'output').mkdir();(self.root/'output'/'private.png').write_bytes(b'not shipped')
  files,errors=release_check.inventory(self.root)
  self.assertEqual(errors,[]);self.assertEqual([f['path'] for f in files],['README.md'])
 def test_unknown_file_and_binary_asset_block_release(self):
  (self.root/'customer.txt').write_text('not an allowed root file')
  (self.root/'examples').mkdir();(self.root/'examples'/'character.png').write_bytes(b'unknown art')
  _,errors=release_check.inventory(self.root);self.assertEqual(len(errors),2)
 def test_local_identity_and_image_payload_patterns_block(self):
  (self.root/'README.md').write_text('/'+'workspace'+'/example/source.png\n'+'data:image/'+'png;base64,'+'A'*100)
  _,errors=release_check.inventory(self.root);self.assertEqual(len(errors),2)
 def test_symlink_blocked(self):
  (self.root/'README.md').symlink_to(self.root/'missing')
  _,errors=release_check.inventory(self.root);self.assertTrue(any('Symlink' in e for e in errors))
 def test_empty_opaque_bytes_not_accepted_as_source(self):
  (self.root/'README.md').write_bytes(b'\xff\xfe')
  _,errors=release_check.inventory(self.root);self.assertTrue(any('Non-UTF8' in e for e in errors))
if __name__=='__main__':unittest.main()
