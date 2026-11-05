import tempfile,unittest
from pathlib import Path
from PIL import Image
import repair_audit as q
class RepairAuditTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name)
  for d in ('a','b','m'):(self.r/d).mkdir()
 def tearDown(self):self.tmp.cleanup()
 def make(self,size=(19,37),count=6):
  for i in range(count):
   im=Image.new('RGBA',size,(50,80,20,255));im.save(self.r/'a'/f'frame-{i:02}.png');im.putpixel((2,3),(1,2,3,255));im.save(self.r/'b'/f'frame-{i:02}.png')
   mask=Image.new('L',size);mask.putpixel((2,3),255);mask.save(self.r/'m'/f'frame-{i:02}.png')
 def audit(self,**kw):return q.audit(self.r/'a',self.r/'b',self.r/'m',**kw)
 def test_variable_sizes_counts_and_inside_edit(self):
  for sz,n in [((19,37),6),((43,21),12)]:
   self.make(sz,n);r=self.audit();self.assertTrue(r['invariantsPass']);self.assertFalse(r['visualApproval']);self.assertEqual(len(r['frames']),n)
 def test_unapproved_change_rejected(self):
  self.make();p=self.r/'b/frame-02.png';im=Image.open(p);im.putpixel((8,20),(0,0,0,0));im.save(p)
  r=self.audit();self.assertFalse(r['invariantsPass']);self.assertEqual(r['frames'][2]['outsideAllowedPixels'],1)
 def test_missing_mask_rejected(self):
  self.make();(self.r/'m/frame-00.png').unlink()
  with self.assertRaises(ValueError):self.audit()
 def test_changed_count_rejected(self):
  self.make();(self.r/'b/frame-00.png').unlink()
  with self.assertRaises(ValueError):self.audit()
 def test_timing_change_rejected(self):
  self.make();seq=[Image.new('RGB',(19,37),(i*30,0,0)) for i in range(6)]
  for name,d in [('old',40),('new',50)]:seq[0].save(self.r/(name+'.gif'),save_all=True,append_images=seq[1:],duration=d,loop=0)
  self.assertFalse(self.audit(before_gif=self.r/'old.gif',after_gif=self.r/'new.gif')['invariantsPass'])
 def test_changed_repeat_behavior_rejected(self):
  self.make();seq=[Image.new('RGB',(19,37),(i*30,0,0)) for i in range(6)]
  for name,loops in [('old',0),('new',1)]:seq[0].save(self.r/(name+'.gif'),save_all=True,append_images=seq[1:],duration=40,loop=loops)
  r=self.audit(before_gif=self.r/'old.gif',after_gif=self.r/'new.gif');self.assertFalse(r['invariantsPass']);self.assertEqual(r['timing']['afterLoop'],1)
 def test_no_timing_evidence_is_explicit(self):
  self.make();self.assertIsNone(self.audit()['timing'])
if __name__=='__main__':unittest.main()
