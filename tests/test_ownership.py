import unittest,copy
import numpy as np
from demo import demo
from motion import render,render_neutral,pose,export,validate
from ownership import apply_ownership
class OwnershipTests(unittest.TestCase):
 def fixture(self):
  _,r,l=demo('side');r.update(walkStyle='simple',hipAttachment={'mode':'split-cloth','confirmed':True});r['jointMeshes']=[{'parent':s+'_thigh','child':s+'_shin','radius':10} for s in ['left','right']];l.update({'walk:'+s+'_thigh':l[s+'_thigh'].copy() for s in ['left','right']});box=l['right_shin'].getbbox();x=(box[0]+box[2])/2;r['walkOwnership']={'confirmed':True,'keepPolygons':{'right_shin':[[x,0],[384,0],[384,384],[x,384]]}};return r,l
 def test_alpha_only_nonmutation_and_positive_part(self):
  r,l=self.fixture();before=l['right_shin'].tobytes();o=apply_ownership(r,l);a=np.array(l['right_shin']);b=np.array(o['right_shin']);self.assertTrue(np.array_equal(a[:,:,:3],b[:,:,:3]));self.assertTrue(np.all(b[:,:,3]<=a[:,:,3]));self.assertTrue(np.any(b[:,:,3]<a[:,:,3]));self.assertIsNotNone(o['right_shin'].getbbox());self.assertEqual(l['right_shin'].tobytes(),before)
 def test_action_pose_and_export(self):
  r,l=self.fixture();old=copy.deepcopy(r);old.pop('walkOwnership');self.assertEqual(pose(r,'walk',.25),pose(old,'walk',.25));self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(old,l).tobytes());self.assertEqual(render(r,l,'dash',.25)[0].tobytes(),render(old,l,'dash',.25)[0].tobytes());self.assertNotEqual(render(r,l,'walk',.25)[0].tobytes(),render(old,l,'walk',.25)[0].tobytes());self.assertEqual(export(r,l,'walk')[1]['walkOwnershipParts'],['right_shin'])
 def test_confirmation_selection_and_coordinates(self):
  r,_=self.fixture()
  for c in [{'confirmed':'true','keepPolygons':r['walkOwnership']['keepPolygons']},{'confirmed':True,'keepPolygons':{'head':[[0,0],[384,0],[0,384]]}},{'confirmed':True,'keepPolygons':{'right_shin':[[0,0],[400,0],[0,384]]}},{'confirmed':True,'keepPolygons':{'right_shin':[[0,0],[float('nan'),0],[0,384]]}}]:
   with self.assertRaises(ValueError):validate({**r,'walkOwnership':c})
  with self.assertRaises(ValueError):validate({**r,'view':'front'})
 def test_empty_and_degenerate_rejected(self):
  r,l=self.fixture();r['walkOwnership']['keepPolygons']['right_shin']=[[0,0],[1,0],[0,1]]
  with self.assertRaises(ValueError):apply_ownership(r,l)
  r['walkOwnership']['keepPolygons']['right_shin']=[[0,0],[1,1],[2,2]]
  with self.assertRaises(ValueError):validate(r)
