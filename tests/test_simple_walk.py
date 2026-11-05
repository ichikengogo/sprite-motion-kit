import unittest,math
from demo import demo
from motion import pose,export,validate,render_neutral,gait_config
class SimpleWalkTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',motionScale=.48);return r,l
 def test_default_eight_frame_export(self):
  r,l=self.fixture();sheet,m=export(r,l,'walk');self.assertEqual(len(m['frames']),8);self.assertEqual(m['fps'],8);self.assertEqual(m['duration'],1);self.assertEqual(sheet.size,(2304,768));self.assertEqual([x['time'] for x in m['frames']],[i/8 for i in range(8)])
 def test_side_only_and_preserved_neutral_dash(self):
  r,l=self.fixture();old={**r,'walkStyle':'wide-stable'}
  self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(old,l).tobytes())
  for i in range(24):self.assertEqual(pose(r,'dash',i/24),pose(old,'dash',i/24))
  with self.assertRaisesRegex(ValueError,'side-view'):validate({**r,'view':'front'})
 def test_keypose_levels_and_fixed_pitch(self):
  r,l=self.fixture();frames=[pose(r,'walk',i/8) for i in range(8)]
  for start in (0,4):
   y=[frames[start+j][0]['head'][0][1] for j in range(4)];self.assertGreater(y[1],y[0]);self.assertLess(y[3],y[2])
  self.assertAlmostEqual(max(x[0]['head'][1] for x in frames),min(x[0]['head'][1] for x in frames))
  self.assertEqual(pose(r,'walk',0),pose(r,'walk',1))
  self.assertEqual(gait_config(r,'walk')['stride'],170)
  for _,ds in frames:self.assertTrue(any(d['contact'] for d in ds))
