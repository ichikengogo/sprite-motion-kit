import os
import unittest
from unittest.mock import Mock,patch
import blas_capabilities as probe

class BlasCapabilitiesTests(unittest.TestCase):
 def setUp(self):
  self.flags=set(probe.REQUIRED_FLAGS['Haswell'])
  self.openblas=[{'user_api':'blas','internal_api':'openblas','architecture':'Haswell'}]
 def test_flags_are_intersected_and_missing_flags_fail_closed(self):
  info='processor: 0\nflags: avx avx2 fma\n\nprocessor: 1\nflags: avx fma\n'
  self.assertEqual(probe.common_cpu_flags(info),{'avx','fma'})
  self.assertEqual(probe.common_cpu_flags(info+'\nprocessor: 2\nmodel: unknown\n'),set())
  self.assertEqual(probe.common_cpu_flags('model: unknown\n'),set())
 def test_requires_matching_platform_features_and_unambiguous_openblas(self):
  self.assertIsNone(probe.support_reason('Haswell','linux','x86_64',self.flags,self.openblas))
  self.assertIsNotNone(probe.support_reason('Haswell','darwin','x86_64',self.flags,self.openblas))
  self.assertIsNotNone(probe.support_reason('Haswell','linux','aarch64',self.flags,self.openblas))
  self.assertIsNotNone(probe.support_reason('Haswell','linux','x86_64',self.flags-{'avx2'},self.openblas))
  self.assertIsNone(probe.support_reason('Sandybridge','linux','x86_64',self.flags-{'avx2'},self.openblas))
  self.assertIsNotNone(probe.support_reason('Haswell','linux','x86_64',self.flags,[{'user_api':'blas','internal_api':'mkl'}]))
  self.assertIsNotNone(probe.support_reason('Haswell','linux','x86_64',self.flags,self.openblas*2))
  self.assertIsNotNone(probe.support_reason('Unknown','linux','x86_64',self.flags,self.openblas))
 def test_selected_kernel_is_verified(self):
  self.assertIsNone(probe.backend_reason(self.openblas,'haswell'))
  self.assertIsNotNone(probe.backend_reason(self.openblas,'Sandybridge'))
  self.assertIsNotNone(probe.backend_reason([{'user_api':'blas','internal_api':'openblas'}],'Haswell'))
 def test_unsupported_backend_never_launches_subprocess(self):
  with patch.dict(os.environ,{'SPRITE_REQUIRE_OPENBLAS_CHECKS':'0'}),patch.object(probe,'probe_reason',return_value='no OpenBLAS'),patch.object(probe.subprocess,'run') as run:
   with self.assertRaises(unittest.SkipTest):probe.run_with_kernel('Haswell','raise AssertionError()')
   run.assert_not_called()
 def test_mkl_or_missing_cpu_feature_never_launches_subprocess(self):
  cpuinfo='processor: 0\nflags: '+' '.join(sorted(self.flags))+'\n'
  cases=[(cpuinfo,[{'user_api':'blas','internal_api':'mkl'}]),
         ('processor: 0\nflags: avx xsave\n',self.openblas)]
  for info,pools in cases:
   with self.subTest(info=info,pools=pools),patch.dict(os.environ,{'SPRITE_REQUIRE_OPENBLAS_CHECKS':'0'}),patch.object(probe.sys,'platform','linux'),patch.object(probe.platform,'machine',return_value='x86_64'),patch.object(probe.Path,'read_text',return_value=info),patch.object(probe,'pool_info',return_value=pools),patch.object(probe.subprocess,'run') as run:
    with self.assertRaises(unittest.SkipTest):probe.run_with_kernel('Haswell','raise AssertionError()')
    run.assert_not_called()
 def test_missing_inspector_fails_closed(self):
  cpuinfo='processor: 0\nflags: '+' '.join(sorted(self.flags))+'\n'
  with patch.dict(os.environ,{'SPRITE_REQUIRE_OPENBLAS_CHECKS':'0'}),patch.object(probe.sys,'platform','linux'),patch.object(probe.platform,'machine',return_value='x86_64'),patch.object(probe.Path,'read_text',return_value=cpuinfo),patch.object(probe,'pool_info',side_effect=ImportError),patch.object(probe.subprocess,'run') as run:
   with self.assertRaises(unittest.SkipTest):probe.run_with_kernel('Haswell','raise AssertionError()')
   run.assert_not_called()
 def test_unselected_kernel_skips_or_fails_in_required_ci(self):
  response=Mock(stdout='{"skip":"kernel not selected"}')
  with patch.object(probe,'probe_reason',return_value=None),patch.object(probe.subprocess,'run',return_value=response):
   with patch.dict(os.environ,{'SPRITE_REQUIRE_OPENBLAS_CHECKS':'0'}):
    with self.assertRaises(unittest.SkipTest):probe.run_with_kernel('Haswell','payload=1')
   with patch.dict(os.environ,{'SPRITE_REQUIRE_OPENBLAS_CHECKS':'1'}):
    with self.assertRaisesRegex(AssertionError,'kernel not selected'):probe.run_with_kernel('Haswell','payload=1')

if __name__=='__main__':unittest.main()
