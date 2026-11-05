import unittest,copy
from PIL import Image
from demo import demo
from motion import render,render_neutral,pose,export
class WalkMaterialTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',motionScale=.48,hipAttachment={'mode':'split-cloth','confirmed':True});r['jointMeshes']=[{'parent':s+'_thigh','child':s+'_shin','radius':10} for s in ('left','right')];l.update({'walk:'+s+'_thigh':l[s+'_thigh'].copy() for s in ('left','right')});n=dict(l);im=Image.new('RGBA',(384,384),(90,80,70,0));im.putalpha(l['left_shin'].getchannel('A'));n['walk:left_shin']=im;return r,l,n
 def test_rgb_only_and_action_scope(self):
  r,l,n=self.fixture();a=render(r,l,'walk',0)[0];b=render(r,n,'walk',0)[0];self.assertEqual(a.getchannel('A').tobytes(),b.getchannel('A').tobytes());self.assertNotEqual(a.tobytes(),b.tobytes());self.assertEqual(render(r,l,'dash',0)[0].tobytes(),render(r,n,'dash',0)[0].tobytes());self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(r,n).tobytes())
 def test_silhouette_change_rejected(self):
  r,l,n=self.fixture();n['walk:left_shin']=Image.new('RGBA',(384,384),'red')
  with self.assertRaises(ValueError):render(r,n,'walk',0)
 def test_invalid_layer_rejected(self):
  for im in [Image.new('RGBA',(10,10),'red'),Image.new('RGBA',(384,384)),Image.new('RGB',(384,384))]:
   r,l,n=self.fixture();n['walk:left_shin']=im
   with self.assertRaises(ValueError):render(r,n,'walk',0)
 def test_export_disclosure_and_no_input_mutation(self):
  r,l,n=self.fixture();old=n['left_shin'].tobytes();_,meta=export(r,n,'walk');self.assertIn('left_shin',meta['walkMaterialParts']);self.assertEqual(old,n['left_shin'].tobytes())
