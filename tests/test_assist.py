import unittest,copy
from PIL import Image,ImageDraw
from demo import demo
from assist import suggest,parse_command
from motion import validate
import test_api as api
class AssistTests(unittest.TestCase):
 def test_three_flattened_views_candidates_unconfirmed(self):
  for view in ('front','side','back'):
   im,_,_=demo(view);before=im.tobytes();r,report=suggest(im,view);validate(r,im)
   self.assertFalse(r['confirmed']);self.assertTrue(all(not p['confirmed'] for p in r['parts'].values()));self.assertEqual(im.tobytes(),before)
   self.assertEqual(report['confidence'],'low');self.assertEqual(report['emptyParts'],[]);self.assertGreater(report['overlapVisiblePixels'],0);self.assertIn('未生成',' '.join(report['warnings']))
 def test_bbox_alignment_not_only_fixed_demo(self):
  im,_,_=demo('front');small=im.resize((230,230));shifted=Image.new('RGBA',(384,384));shifted.paste(small,(40,55))
  r,report=suggest(shifted,'front');self.assertNotEqual(r['root'],[192,210]);self.assertEqual(report['bounds'],list(shifted.getchannel('A').point(lambda a:255 if a>=32 else 0).getbbox()))
 def test_malformed_or_unsupported_input(self):
  cases=[Image.new('RGBA',(384,384)),Image.new('RGBA',(384,384),'white'),Image.new('RGBA',(10,10)),Image.new('RGB',(384,384))]
  for im in cases:
   with self.assertRaises(ValueError):suggest(im,'front')
  wide=Image.new('RGBA',(384,384));ImageDraw.Draw(wide).rectangle((20,100,360,180),fill='white')
  with self.assertRaises(ValueError):suggest(wide,'front')
  with self.assertRaises(ValueError):suggest(demo('front')[0],'diagonal')
 def test_strict_commands(self):
  for word in ('歩行','歩く','walk',' WALK '):self.assertEqual(parse_command(word),'walk')
  for word in ('ダッシュ','走る','run','dash'):self.assertEqual(parse_command(word),'dash')
  for word in ('walk and dash','歩かない','飛ぶ','run slowly','',None,3,'a'*81):
   with self.assertRaises(ValueError):parse_command(word)
class AssistApiTests(unittest.TestCase):
 setUpClass=classmethod(api.ApiTests.setUpClass.__func__)
 tearDownClass=classmethod(api.ApiTests.tearDownClass.__func__)
 request=api.ApiTests.request
 base=api.ApiTests.base
 def test_suggestion_gate_and_parser(self):
  d=self.base();code,raw=self.request({'image':d['image'],'view':'side'},'/api/suggest');self.assertEqual(code,200)
  import json
  result=json.loads(raw);d['rig']=result['rig'];d['demo']=False;self.assertFalse(d['rig']['confirmed']);self.assertEqual(self.request(d)[0],400)
  code,raw=self.request({'command':'走る'},'/api/command');self.assertEqual(code,200);self.assertEqual(json.loads(raw)['action'],'dash')
  self.assertEqual(self.request({'command':'飛ぶ'},'/api/command')[0],400)
  self.assertEqual(self.request({'image':'not a png','view':'side'},'/api/suggest')[0],400)
if __name__=='__main__':unittest.main()
