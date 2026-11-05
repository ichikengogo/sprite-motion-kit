import copy,unittest
import numpy as np
import test_projected_walk
from projected_walk import validate,mapper_for,render

class ProjectedRigidRegionTests(unittest.TestCase):
 def fixture(self):
  rig,layers=test_projected_walk.ProjectedWalkTests().fixture('back')
  rig['projectedWalk']['rigidRegions']=[{'box':[142,192,170,232],'feather':12}]
  return rig,layers
 def test_core_is_rigid_body_translation_and_uniform_display_scale(self):
  rig,_=self.fixture();validate(rig)
  neutral=mapper_for(rig,0,True)
  for phase in np.arange(24)/24:
   mapper=mapper_for(rig,float(phase));points=[np.array(p,float) for p in ([142,192],[170,232],[149,215],[163,224])]
   displacement=mapper(points[0])-neutral(points[0])
   for point in points:
    np.testing.assert_allclose(mapper(point)-neutral(point),displacement,atol=1e-12)
   for a,b in zip(points,points[1:]):
    np.testing.assert_allclose(mapper(b)-mapper(a),neutral(b)-neutral(a),atol=1e-12)
 def test_unconfigured_and_empty_regions_are_byte_identical(self):
  rig,layers=self.fixture();rig['projectedWalk'].pop('rigidRegions');explicit=copy.deepcopy(rig);explicit['projectedWalk']['rigidRegions']=[]
  for phase in (0,.375):
   a,_=render(rig,layers,phase);b,_=render(explicit,layers,phase);self.assertEqual(a.tobytes(),b.tobytes())
 def test_outside_unchanged_neutral_unchanged_and_boundary_continuous(self):
  rig,_=self.fixture();legacy=copy.deepcopy(rig);legacy['projectedWalk'].pop('rigidRegions')
  for phase in (0,.125,.5,.75):
   mapper=mapper_for(rig,phase);old=mapper_for(legacy,phase)
   for p in ([192,85],[210,310],[130,260],[200,230]):np.testing.assert_array_equal(mapper(np.array(p,float)),old(np.array(p,float)))
   for p in ([145,202],[163,232]):np.testing.assert_array_equal(mapper_for(rig,phase,True)(np.array(p,float)),mapper_for(legacy,phase,True)(np.array(p,float)))
   for x in (130,142,170,182):
    self.assertLess(np.linalg.norm(mapper(np.array([x-1e-6,215]))-mapper(np.array([x+1e-6,215]))),1e-4)
 def test_malformed_and_below_hip_regions_reject(self):
  rig,_=self.fixture()
  for bad in (None,{},[{'box':[142,192,170,238],'feather':12}],[{'box':[142,192,170,232],'feather':True}],[{'box':[142,192,170,float('nan')],'feather':12}],[{'box':[142,192,170,232],'feather':3}],[{'box':[142,192,170,232],'feather':12,'extra':1}],[{'box':[142,192,170,232],'feather':12}]*5):
   candidate=copy.deepcopy(rig);candidate['projectedWalk']['rigidRegions']=bad
   with self.assertRaises(ValueError):validate(candidate)

if __name__=='__main__':unittest.main()
