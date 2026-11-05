import copy,math,unittest
import numpy as np
from PIL import Image
from demo import demo
from motion import pose,render,validate
from joint_mesh import joint_mapper,draw_mapped

class CuffNormalTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',motionScale=.4)
  r['jointMeshes']=[dict(parent=s+'_thigh',child=s+'_shin',radius=18,walkContour='centerline') for s in ('left','right')]
  return r,l
 def test_pose_contacts_bones_and_dash_unchanged(self):
  r,l=self.fixture();q=copy.deepcopy(r)
  for m in q['jointMeshes']:m['walkCuffNormal']={'startY':240,'endY':270}
  validate(q)
  for i in range(24):self.assertEqual(pose(r,'walk',i/24),pose(q,'walk',i/24))
  self.assertEqual(r['parts'],q['parts'])
  self.assertEqual(render(r,l,'dash',.25)[0].tobytes(),render(q,l,'dash',.25)[0].tobytes())
 def test_default_mapper_identical_and_band_changes_only_normal(self):
  r,l=self.fixture();tr,_=pose(r,'walk',.79);a=joint_mapper(r,tr,'left_thigh','left_shin',18,'centerline');b=joint_mapper(r,tr,'left_thigh','left_shin',18,'centerline',cuff_normal=None)
  c=joint_mapper(r,tr,'left_thigh','left_shin',18,'centerline',cuff_normal={'startY':240,'endY':270})
  joint=np.array(r['parts']['left_shin']['start'],float);axis=np.array(r['parts']['left_shin']['end'])-joint;axis/=np.linalg.norm(axis)
  for y in range(220,310,5):
   for x in range(150,220,5):np.testing.assert_array_equal(a(np.array([x,y],float)),b(np.array([x,y],float)))
  for u in range(-30,31,5):np.testing.assert_allclose(a(joint+u*axis),c(joint+u*axis),atol=1e-12)
  # Renderer samples supplied pixels; constant original material cannot become invented colors.
  im=Image.new('RGBA',(384,384));im.paste((30,70,110,255),(160,240,200,290));out=np.array(draw_mapped(im,c));rgb=out[out[:,:,3]>128,:3]
  self.assertTrue(np.all(np.abs(rgb.astype(int)-[30,70,110])<=1))
 def test_invalid_settings(self):
  bad=[None,False,{}, {'startY':240,'endY':240},{'startY':0,'endY':270},{'startY':240,'endY':385},{'startY':True,'endY':270},{'startY':240,'endY':float('nan')},{'startY':240,'endY':270,'x':1}]
  for setting in bad:
   r,_=self.fixture();r['jointMeshes'][0]['walkCuffNormal']=setting
   with self.assertRaises(ValueError):validate(r)
  for key,value in [('view','front'),('walkStyle','cautious')]:
   r,_=self.fixture();r[key]=value;r['jointMeshes'][0]['walkCuffNormal']={'startY':240,'endY':270}
   with self.assertRaises(ValueError):validate(r)
  r,_=self.fixture();r['jointMeshes'][0].update(walkContour='rotation',walkCuffNormal={'startY':240,'endY':270})
  with self.assertRaises(ValueError):validate(r)
