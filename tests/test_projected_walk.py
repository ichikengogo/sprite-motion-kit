import unittest,copy
import numpy as np
from PIL import Image,ImageDraw
from demo import demo
from projected_walk import validate,mapper_for,source_image,render,export
class ProjectedWalkTests(unittest.TestCase):
 def fixture(self,view='front'):
  _,r,_=demo(view);r['projectedWalk']={'confirmed':True,'hip':237,'knee':280,'ankle':317,'shoulder':156,'hand':270,'armInner':157,'armOuter':139,'legScale':1.3,'neutralHeight':317,'ground':349,'centerX':192,'strideDepth':36,'lift':12,'depthProjection':.28,'shoeProjection':.2}
  layers={}
  for i,n in enumerate(r['order']):
   im=Image.new('RGBA',(384,384));ImageDraw.Draw(im).rectangle((140,32+i*26,244,57+i*26),fill=(50+i*10,70,100,255));layers[n]=im
  return r,layers
 def test_gates_and_bounds(self):
  r,_=self.fixture();validate(r)
  for key,value in [('confirmed',False),('legScale',float('nan')),('strideDepth',100),('neutralHeight',300)]:
   q=copy.deepcopy(r);q['projectedWalk'][key]=value
   with self.assertRaises(ValueError):validate(q)
  r['view']='side'
  with self.assertRaises(ValueError):validate(r)
 def test_unreachable_rejected(self):
  r,_=self.fixture();r['projectedWalk'].update(knee=253,ankle=269,strideDepth=40,legScale=1)
  with self.assertRaisesRegex(ValueError,'unreachable'):mapper_for(r,0)(np.array([180,290],float))
 def test_optional_arm_fade_has_continuous_end(self):
  r,_=self.fixture();r['projectedWalk'].update(hand=252,armInner=160,armFadeDepth=24);validate(r)
  for t in (0,.125,.25,.5,.75):
   m=mapper_for(r,t)
   for y in (252,260,276):
    a=m(np.array([155,y-1e-6]));b=m(np.array([155,y+1e-6]));self.assertLess(np.linalg.norm(b-a),1e-4)
  r['projectedWalk']['armFadeDepth']=8
  with self.assertRaises(ValueError):validate(r)
 def test_dynamic_preserves_neutral_head_and_increases_step(self):
  r,_=self.fixture();strong=copy.deepcopy(r);strong['projectedWalk'].update(strideDepth=48,lift=18,depthProjection=.45,armAmplitude=9,armSpread=3.5);validate(strong)
  old=[];new=[]
  for i in range(49):
   t=i/48;a=mapper_for(r,t);b=mapper_for(strong,t);np.testing.assert_array_equal(a(np.array([192,100.])),b(np.array([192,100.])));old.append(a(np.array([180,349.]))[1]);new.append(b(np.array([180,349.]))[1])
  self.assertGreater(np.ptp(new),np.ptp(old)*1.3)
  for p in ([180,290.],[204,325.],[146,252.]):np.testing.assert_array_equal(mapper_for(r,0,True)(np.array(p)),mapper_for(strong,0,True)(np.array(p)))
 def test_legacy_arm_defaults_and_limits(self):
  r,_=self.fixture();explicit=copy.deepcopy(r);explicit['projectedWalk'].update(armAmplitude=6,armSpread=2)
  for t in (0,.25,.5,.75):np.testing.assert_array_equal(mapper_for(r,t)(np.array([146,250.])),mapper_for(explicit,t)(np.array([146,250.])))
  explicit['projectedWalk']['armAmplitude']=11
  with self.assertRaises(ValueError):validate(explicit)
 def test_linear_leg_surface_avoids_recovery_pinch(self):
  r,_=self.fixture();r['projectedWalk'].update(hip=235.4,knee=288,ankle=315.3,strideDepth=48,lift=18,depthProjection=.45,armAmplitude=9,armSpread=3.5,armFadeDepth=24,legInterpolation='linear');validate(r)
  for t in np.linspace(0,1,97):
   m=mapper_for(r,t);values=[m(np.array([216,y]))[1] for y in np.linspace(288,315.3,20)];self.assertGreater(min(np.diff(values)),.1)
  r['projectedWalk']['legInterpolation']='unknown'
  with self.assertRaises(ValueError):validate(r)
 def test_exclusive_ownership(self):
  r,l=self.fixture();source_image(r,l);l[r['order'][1]]=l[r['order'][0]].copy()
  with self.assertRaisesRegex(ValueError,'exclusive'):source_image(r,l)
 def test_loop_and_positive_local_geometry(self):
  for view in ('front','back'):
   r,_=self.fixture(view)
   for t in np.linspace(0,1,49):
    m=mapper_for(r,t)
    for x,y in ((180,250),(180,285),(180,325),(204,250),(204,285),(204,325)):
     p=np.array([x,y],float);j=np.column_stack(((m(p+[.001,0])-m(p))/.001,(m(p+[0,.001])-m(p))/.001));self.assertGreater(np.linalg.det(j),0)
   for p in ([180,250],[204,325],[146,270]):np.testing.assert_allclose(mapper_for(r,0)(np.array(p)),mapper_for(r,1)(np.array(p)))
 def test_export_draft_and_dash_block(self):
  r,l=self.fixture();sheet,meta=export(r,l,'walk',2);self.assertEqual(len(meta['frames']),2);self.assertFalse(meta['quality']['approved']);self.assertEqual(meta['duration'],1)
  with self.assertRaises(ValueError):export(r,l,'dash')
if __name__=='__main__':unittest.main()
