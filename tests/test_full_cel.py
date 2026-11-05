"""Generic full-cel and view-specific owner vocabulary, no private character assets."""
import unittest
from PIL import Image
import test_drawn_cel
from drawn_cel import validate,pin_sources,render_frames
class FullCelTests(unittest.TestCase):
 setUp=test_drawn_cel.DrawnCelTests.setUp
 tearDown=test_drawn_cel.DrawnCelTests.tearDown
 save=test_drawn_cel.DrawnCelTests.save
 def full(self):
  self.p['representation']='coherent-full-cel'
  for k in ('upperCel','upperTranslationX','upperAnchorY'):self.p.pop(k,None)
  self.p['registration']=[{'source':f'{i}.png','scale':1,'translation':[0,0]} for i in range(self.p['frames'])]
  self.save();pin_sources(self.path)
 def test_whole_cells_need_no_waist_or_upper(self):
  self.full();fs=render_frames(self.path)
  for i,f in enumerate(fs):self.assertEqual(f.crop((0,0,12,10)).tobytes(),Image.open(self.root/f'{i}.png').convert('RGBA').tobytes())
 def test_front_back_anatomical_identity_not_near_far(self):
  self.full();self.p['legOwners']=['anatomical-left','anatomical-right']
  for r in self.p['phaseMetadata']:
   r['supportOwner']='anatomical-left' if r['supportOwner']=='near' else 'anatomical-right';r['swingOwner']='anatomical-left' if r['swingOwner']=='near' else 'anatomical-right'
  self.save();pin_sources(self.path);self.assertEqual(len(render_frames(self.path)),4)
 def test_invalid_owner_pair(self):
  self.p['legOwners']=['same','same'];self.save()
  with self.assertRaisesRegex(ValueError,'distinct'):validate(self.path)
 def test_full_cel_cannot_silently_apply_waist_crop(self):
  self.full();self.p['registration'][0]['clipRects']=[[0,0,2,2]];self.save()
  with self.assertRaisesRegex(ValueError,'Full cels'):validate(self.path)
 def test_unknown_representation(self):
  self.p['representation']='automatic-anatomy';self.save()
  with self.assertRaisesRegex(ValueError,'representation'):validate(self.path)
