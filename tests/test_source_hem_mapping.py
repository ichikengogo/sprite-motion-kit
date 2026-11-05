import copy,hashlib,json,os,platform,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import test_garment
from garment import panel_hem_x
from joint_mesh import _rgba8
from motion import render,validate,pose

PHASES=(0,.25,.5,.75)
# Full RGBA-frame hashes for the synthetic legacy registered-width fixture.
EXPECTED=['4cb3a9741c3498bc57078a7db7f4c0530ae250f23caef7cf59e05a926b7d39b9','954c25554b6ce21e2f1c9947f43a5e80eccadb249d54e863bf000a1c1a409508','63918c9dadbdf1cab4dfba1661484d56bfbe76e8d94f88d2f1bdfdf4d3d2a76e','6c3a236dc8f819dd47df164d707945b0d2d49574a346a2f6e39610c57b4decc4']
# The pre-fix renderer, captured independently on the Haswell OpenBLAS kernel.
PRE_FIX_HASWELL=['2769e03beecfeca01347fbaa19a8ad1b799d5e0784206c61c1674c5134a940b8','bdc308be6af12b0657ed319beceb4ad0926a4c6d9aaa302fc13f2bed137955d1','e3bc48aae2836ff463bb69072e65b4527358b77095f6a831b11cf5054fc52407','563ce9677b954f3e7fc4e07d8220c29255d2eb7616f7a84e674b16f80b09d4a5']

class SourceHemMappingTests(unittest.TestCase):
 def fixture(self):
  r,l=test_garment.GarmentTests().fixture()
  r['walkGarment']['hemConnection']={'mode':'skin-mesh','overlap':1}
  return r,l
 def test_preserve_source_x_not_box_to_hem_compression(self):
  panel={'sourceBox':[150,239,191,275],'hemX':[164,187],'skinStart':275}
  cfg={'sourceHemMode':'preserve-x'}
  for x in (150,157.5,164,175,187,191):self.assertEqual(panel_hem_x(cfg,panel,x),x)
  self.assertEqual(panel_hem_x({},panel,150),164)
  self.assertEqual(panel_hem_x({},panel,191),187)
  self.assertNotEqual(panel_hem_x({},panel,164),164)
 def test_legacy_raster_golden_frames(self):
  # Hash every byte; no per-pixel tolerance or aggregate similarity threshold.
  r,l=self.fixture()
  for phase,h in zip(PHASES,EXPECTED):self.assertEqual(hashlib.sha256(render(r,l,'walk',phase)[0].tobytes()).hexdigest(),h)
 def test_legacy_digest_detects_wrong_hem_mapping(self):
  r,l=self.fixture()
  with patch('garment.panel_hem_x',side_effect=lambda config,panel,x:x):
   actual=hashlib.sha256(render(r,l,'walk',0)[0].tobytes()).hexdigest()
  self.assertNotEqual(actual,EXPECTED[0])
 def test_quantization_stabilizes_only_subchannel_boundary_noise(self):
  values=np.array([-1,69.9999998,70-1e-10,70+1e-10,70.0000002,256],dtype=float)/255
  np.testing.assert_array_equal(_rgba8(values),[0,69,70,70,70,255])
 @unittest.skipUnless(sys.platform.startswith('linux') and platform.machine().lower() in ('x86_64','amd64'),'OpenBLAS x86 dispatch check')
 def test_legacy_raster_with_alternate_blas_kernels(self):
  # OpenBLAS selects its CPU kernel when the library is loaded.
  script='''import hashlib,json\nfrom test_source_hem_mapping import SourceHemMappingTests,PHASES\nfrom motion import render\nr,l=SourceHemMappingTests().fixture()\nprint(json.dumps([hashlib.sha256(render(r,l,"walk",p)[0].tobytes()).hexdigest() for p in PHASES]))'''
  for core in ('Haswell','Sandybridge'):
   with self.subTest(core=core):
    env=os.environ.copy(); env['OPENBLAS_CORETYPE']=core
    env['PYTHONPATH']=os.pathsep.join(filter(None,[str(Path(__file__).resolve().parent),env.get('PYTHONPATH','')]))
    result=subprocess.run([sys.executable,'-c',script],env=env,capture_output=True,text=True,check=True,timeout=60)
    self.assertEqual(json.loads(result.stdout),EXPECTED)
 @unittest.skipUnless(sys.platform.startswith('linux') and platform.machine().lower() in ('x86_64','amd64'),'OpenBLAS x86 reference')
 def test_preserves_pre_fix_raster_silhouette_and_color(self):
  # Reproduce the original byte conversion; its independently captured hashes
  # guard against a shared change to the renderer used on both sides below.
  script='''import hashlib,json\nimport numpy as np\nfrom unittest.mock import patch\nfrom test_source_hem_mapping import SourceHemMappingTests,PHASES\nfrom motion import render\nr,l=SourceHemMappingTests().fixture()\nresults=[]\nfor phase in PHASES:\n with patch("joint_mesh._rgba8",side_effect=lambda rgba:np.uint8(np.clip(rgba*255,0,255))):\n  old=np.asarray(render(r,l,"walk",phase)[0])\n new=np.asarray(render(r,l,"walk",phase)[0])\n diff=np.abs(old.astype(np.int16)-new.astype(np.int16))\n results.append({"old_hash":hashlib.sha256(old.tobytes()).hexdigest(),"max_delta":int(diff.max()),"changed_pixels":int(np.any(diff,axis=2).sum()),"mask_changed":int(np.count_nonzero((old[:,:,3]>0)!=(new[:,:,3]>0))),"alpha_delta":int(diff[:,:,3].max())})\nprint(json.dumps(results))'''
  env=os.environ.copy();env['OPENBLAS_CORETYPE']='Haswell'
  env['PYTHONPATH']=os.pathsep.join(filter(None,[str(Path(__file__).resolve().parent),env.get('PYTHONPATH','')]))
  result=subprocess.run([sys.executable,'-c',script],env=env,capture_output=True,text=True,check=True,timeout=60)
  frames=json.loads(result.stdout);self.assertEqual(len(frames),len(PRE_FIX_HASWELL))
  for expected,frame in zip(PRE_FIX_HASWELL,frames):
   self.assertEqual(frame['old_hash'],expected)
   self.assertEqual(frame['mask_changed'],0)
   self.assertLessEqual(frame['alpha_delta'],1)
   self.assertLessEqual(frame['max_delta'],4)
   self.assertLessEqual(frame['changed_pixels'],1500)
 def test_optin_no_pose_material_or_dash_mutation(self):
  r,l=self.fixture();old=copy.deepcopy(r);saved={n:im.tobytes() for n,im in l.items()}
  r['walkGarment']['sourceHemMode']='preserve-x';validate(r);confirmed=copy.deepcopy(r)
  for t in (0,.25,.5,.75):
   self.assertEqual(pose(r,'walk',t),pose(old,'walk',t));render(r,l,'walk',t)
  self.assertEqual(r,confirmed);self.assertEqual(saved,{n:im.tobytes() for n,im in l.items()})
  self.assertEqual(render(r,l,'dash',0)[0].tobytes(),render(old,l,'dash',0)[0].tobytes())
 def test_bad_mode_or_missing_connection_rejected(self):
  r,l=self.fixture()
  for value in (True,None,'guess',''):
   q=copy.deepcopy(r);q['walkGarment']['sourceHemMode']=value
   with self.assertRaises(ValueError):validate(q)
  r['walkGarment']['sourceHemMode']='preserve-x';del r['walkGarment']['hemConnection']
  with self.assertRaises(ValueError):validate(r)

class SparseSourceHemGuardTests(unittest.TestCase):
 def fixture(self,active_fold=False):
  import math
  import numpy as np
  from PIL import Image,ImageDraw
  r,l=test_garment.GarmentTests().fixture();r['walkGarment'].update(sourceHemMode='preserve-x',hemConnection={'mode':'skin-mesh','overlap':1})
  for side,p in r['walkGarment']['panels'].items():
   x0,y0,x1,y1=p['sourceBox'];im=Image.new('RGBA',(384,384));ImageDraw.Draw(im).rectangle((x0 if active_fold else x0+8,y0+3,x1-8,y1-3),fill=(50,40,30,255));l['walk:garment_'+side]=im
  transforms={n:(p['start'],math.atan2(p['end'][1]-p['start'][1],p['end'][0]-p['start'][0])) for n,p in r['parts'].items()}
  def mapper_factory(rig,transforms,parent,*args,**kwargs):
   panel=rig['walkGarment']['panels'][parent.split('_')[0]];x0,y0,x1,y1=panel['sourceBox']
   return lambda v:np.array([v[0],y0-10 if v[0]<x0+4 else v[1]],float)
  return r,l,transforms,mapper_factory
 def test_empty_corner_fold_deferred_to_real_active_mesh(self):
  from unittest.mock import patch
  from garment import apply_garment
  r,l,t,mapper=self.fixture();stats=[]
  with patch('garment.joint_mapper',side_effect=mapper):apply_garment(r,l,t,stats)
  mesh=[s for s in stats if s['side'].startswith('garment_mesh_')]
  self.assertEqual(len(mesh),2);self.assertTrue(all(s['activeInvertedTriangles']==0 and s['areaRatio']>=.08 for s in mesh))
  # Legacy remains conservative and rejects this enclosing quad.
  r['walkGarment'].pop('sourceHemMode')
  with patch('garment.joint_mapper',side_effect=mapper):
   with self.assertRaisesRegex(ValueError,'Garment panel folds/collapses'):apply_garment(r,l,t)
 def test_occupied_fold_still_rejected(self):
  from unittest.mock import patch
  from garment import apply_garment
  r,l,t,mapper=self.fixture(active_fold=True)
  with patch('garment.joint_mapper',side_effect=mapper):
   with self.assertRaisesRegex(ValueError,'Mapped garment folds/collapses'):apply_garment(r,l,t)
