import unittest,copy,math,json,io
from PIL import Image,ImageDraw
from demo import demo
from motion import pose,require_ready,export
import test_api as api
from server import image_data
class FacingAndPartsTests(unittest.TestCase):
 def test_left_side_is_mirrored_kinematics_without_source_flip(self):
  _,right,_=demo('side');left=copy.deepcopy(right);left['facing']='left';left['root'][0]=384-left['root'][0]
  for p in left['parts'].values():
   for key in ('start','end'):p[key]=[384-p[key][0],p[key][1]]
   p['polygon']=[[384-x,y] for x,y in p['polygon']]
  for action in ('walk','dash'):
   for i in range(25):
    a,da=pose(right,action,i/24);b,db=pose(left,action,i/24)
    for name in a:
     self.assertAlmostEqual(a[name][0][0]+b[name][0][0],384,places=7);self.assertAlmostEqual(a[name][0][1],b[name][0][1],places=7)
     self.assertAlmostEqual(math.sin(a[name][1]),math.sin(b[name][1]),places=7);self.assertAlmostEqual(math.cos(a[name][1]),-math.cos(b[name][1]),places=7)
    for x,y in zip(da,db):self.assertAlmostEqual(x['ground_velocity'],-y['ground_velocity'])
 def test_missing_art_blocks_even_when_confirmed(self):
  _,r,l=demo('side');r['parts']['left_forearm']['availability']='missing'
  for action in ('walk','dash'):
   with self.assertRaisesRegex(ValueError,'Missing/unverified'):export(r,l,action)
  r['parts']['left_forearm']['availability']='unverified'
  with self.assertRaises(ValueError):require_ready(r)
class ReplacementApiTests(unittest.TestCase):
 setUpClass=classmethod(api.ApiTests.setUpClass.__func__);tearDownClass=classmethod(api.ApiTests.tearDownClass.__func__);request=api.ApiTests.request;base=api.ApiTests.base
 def test_invalid_layer_size_and_empty_are_rejected(self):
  for im in (Image.new('RGBA',(20,20)),Image.new('RGBA',(384,384))):
   d=self.base();d['demo']=False;d['partImages']={'head':image_data(im)};self.assertEqual(self.request(d)[0],400)
 def test_full_canvas_replacement_is_used(self):
  d=self.base();d['demo']=False;im=Image.new('RGBA',(384,384));ImageDraw.Draw(im).rectangle((180,100,205,125),fill='#ff0000');d['partImages']={'head':image_data(im)}
  code,raw=self.request(d);self.assertEqual(code,200)
  import base64
  sheet=Image.open(io.BytesIO(base64.b64decode(json.loads(raw)['sheet'].split(',')[1])))
  self.assertGreater(sum(p[0]>240 and p[1]<15 and p[2]<15 and p[3]>200 for p in sheet.getdata()),50)
