import copy,unittest
import numpy as np
import test_walk_material
from motion import render,render_neutral,pose,validate,export
from joint_mesh import joint_mapper
class GarmentTests(unittest.TestCase):
 def fixture(self):
  r,l,_=test_walk_material.WalkMaterialTests().fixture();panels={}
  for side in ('left','right'):
   p=r['parts'][side+'_thigh'];x=int(p['start'][0]);y=int(p['start'][1]);bottom=int((p['start'][1]+p['end'][1])/2);panels[side]={'sourceBox':[x-16,y-5,x+16,bottom],'hemX':[x-14,x+14],'skinStart':bottom};l['walk:garment_'+side]=l[side+'_thigh'].copy()
  r['walkGarment']={'mode':'waist-and-tubes','confirmed':True,'panels':panels,'waistBottom':y+5,'waistFeather':3};l['walk:garment_waist']=l['left_thigh'].copy();l['walk:garment_waist'].alpha_composite(l['right_thigh'])
  a=np.array(l['walk:garment_waist']);top=min(p['sourceBox'][1] for p in panels.values());bottom=max(p['sourceBox'][3] for p in panels.values());a[:top]=0;a[bottom:]=0;left=min(p['sourceBox'][0] for p in panels.values());right=max(p['sourceBox'][2] for p in panels.values());a[:,:left]=0;a[:,right:]=0;l['walk:garment_waist']=test_walk_material.Image.fromarray(a)
  for m in r['jointMeshes']:m['walkContour']='centerline'
  return r,l
 def test_nonmutation_scope_and_metadata(self):
  r,l=self.fixture();old=copy.deepcopy(r);saved={n:im.tobytes() for n,im in l.items()};base=copy.deepcopy(r);base.pop('walkGarment');render(r,l,'walk',.25);self.assertEqual(r,old);self.assertEqual(saved,{n:im.tobytes() for n,im in l.items()});self.assertEqual(render(r,l,'dash',0)[0].tobytes(),render(base,l,'dash',0)[0].tobytes());self.assertEqual(render_neutral(r,l).tobytes(),render_neutral(base,l).tobytes());self.assertEqual(pose(r,'walk',.25),pose(base,'walk',.25));_,meta=export(r,l,'walk');self.assertEqual(meta['walkGarment'],r['walkGarment'])
 def test_reject_unconfirmed_bad_bounds_or_missing(self):
  r,l=self.fixture()
  for key,value in [('confirmed',False),('waistFeather',float('nan')),('waistBottom',384)]:
   q=copy.deepcopy(r);q['walkGarment'][key]=value
   with self.assertRaises(ValueError):validate(q)
  q=copy.deepcopy(r);q['walkGarment']['panels']['left']['hemX']=[300,301]
  with self.assertRaises(ValueError):validate(q)
  q=copy.deepcopy(r);q['walkGarment']['panels']['left']['skinStart']=float(q['walkGarment']['panels']['left']['skinStart'])
  with self.assertRaises(ValueError):validate(q)
  del l['walk:garment_left']
  with self.assertRaises(ValueError):render(r,l,'walk',0)
 def test_cycle_and_quads(self):
  r,l=self.fixture();self.assertEqual(render(r,l,'walk',0)[0].tobytes(),render(r,l,'walk',1)[0].tobytes())
  for i in range(8):render(r,l,'walk',i/8)
 def test_mapper_joint_anchor_and_finite(self):
  r,l=self.fixture();t,_=pose(r,'walk',.25);m=r['jointMeshes'][0];mapper=joint_mapper(r,t,m['parent'],m['child'],m['radius'],'centerline');joint=np.array(r['parts'][m['child']]['start']);self.assertTrue(np.isfinite(mapper(joint)).all());self.assertTrue(np.allclose(mapper(joint),t[m['child']][0]))
