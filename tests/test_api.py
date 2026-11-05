"""Local API contract tests, no external network."""
import unittest,threading,json,copy,io,zipfile
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from server import Handler,image_data
from demo import demo
class ApiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.http=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start();cls.url=f'http://127.0.0.1:{cls.http.server_port}'
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.thread.join()
 def request(self,data,path='/api/render',origin=None):
  headers={'Content-Type':'application/json'}
  if origin:headers['Origin']=origin
  try:
   r=urlopen(Request(self.url+path,json.dumps(data).encode(),headers),timeout=60);return r.status,r.read()
  except HTTPError as e:return e.code,e.read()
 def base(self):
  im,rig,_=demo('side');return {'rig':rig,'image':image_data(im),'demo':True,'action':'walk'}
 def test_missing_unconfirmed_and_invalid_order_rejected(self):
  for change in ('rig','part','stringrig','stringpart','missing','order','unknown_action'):
   d=self.base()
   if change=='rig':d['rig']['confirmed']=False
   elif change=='part':d['rig']['parts']['left_foot']['confirmed']=False
   elif change=='stringrig':d['rig']['confirmed']='false'
   elif change=='stringpart':d['rig']['parts']['left_foot']['confirmed']='false'
   elif change=='missing':del d['rig']['parts']['left_foot']
   elif change=='order':d['rig']['order']=['head']
   else:d['action']='teleport'
   code,_=self.request(d);self.assertEqual(code,400)
 def test_foreign_origin_and_empty_mask_blocked(self):
  self.assertEqual(self.request(self.base(),origin='https://untrusted.invalid')[0],400)
  d=self.base();d['demo']=False;d['rig']['parts']['left_foot']['polygon']=[[0,0],[4,0],[4,4]]
  self.assertEqual(self.request(d)[0],400)
 def test_imported_image_path_and_export_zip(self):
  d=self.base();d['demo']=False # Actually exercises PNG decoding + user masks, not demo layers.
  code,raw=self.request(d,'/api/export');self.assertEqual(code,200)
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   self.assertEqual(set(z.namelist()),{'sheet.png','animation.json','rig.json'});m=json.loads(z.read('animation.json'));self.assertEqual(m['status'],'draft');self.assertEqual(len(m['frames']),24)
if __name__=='__main__':unittest.main()
