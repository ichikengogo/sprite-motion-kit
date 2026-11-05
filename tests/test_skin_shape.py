import copy,unittest
from PIL import Image
import test_walk_material
from motion import render,render_neutral,validate,export
class SkinShapeTests(unittest.TestCase):
 def fixture(self):
  r,l,n=test_walk_material.WalkMaterialTests().fixture();n['walk:left_shin']=l['left_shin'].copy();im=n['walk:left_shin'];box=im.getbbox();top=box[1];bottom=min(top+12,int(r['parts']['left_shin']['end'][1]));r['walkSkinShape']={'confirmed':True,'bands':{'left_shin':[top,bottom]}}
  x=box[0];im.putpixel((x,top+2),(30,20,10,255));return r,l,n,top,bottom
 def test_explicit_band_and_no_mutation(self):
  r,l,n,t,b=self.fixture();before=n['left_shin'].tobytes();render(r,n,'walk',0);self.assertEqual(before,n['left_shin'].tobytes());self.assertEqual(render(r,n,'dash',0)[0].tobytes(),render(r,l,'dash',0)[0].tobytes());self.assertEqual(render_neutral(r,n).tobytes(),render_neutral(r,l).tobytes())
 def test_outside_band_and_missing_rejected(self):
  r,l,n,t,b=self.fixture();n['walk:left_shin'].putpixel((0,b),(255,0,0,255))
  with self.assertRaises(ValueError):render(r,n,'walk',0)
  del n['walk:left_shin']
  with self.assertRaises(ValueError):render(r,n,'walk',0)
 def test_invalid_config(self):
  r,l,n,t,b=self.fixture()
  for cfg in [{'confirmed':False,'bands':{'left_shin':[t,b]}},{'confirmed':True,'bands':{'left_shin':[float(t),b]}},{'confirmed':True,'bands':{'left_foot':[t,b]}},{'confirmed':True,'bands':{'left_shin':[0,384]}}]:
   q=copy.deepcopy(r);q['walkSkinShape']=cfg
   with self.assertRaises(ValueError):validate(q)
 def test_export_disclosure(self):
  r,l,n,t,b=self.fixture();_,meta=export(r,n,'walk');self.assertEqual(meta['walkSkinShape'],r['walkSkinShape'])
