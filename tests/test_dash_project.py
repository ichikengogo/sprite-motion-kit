import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
import dash_project as project


class DashProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.path = project.create_demo(self.root / 'fixture')
    def tearDown(self): self.temp.cleanup()
    def update(self, mutate):
        data=json.loads(self.path.read_text());mutate(data);self.path.write_text(json.dumps(data))
    def test_clean_reproduction_preserves_sources_and_rejects_output_reuse(self):
        _, p, _, pins=project.read_project(self.path)
        out=self.root/'rendered'; report=project.export_project(self.path,out)
        self.assertTrue(project.verify_export(self.path,out)['byteExact'])
        self.assertEqual(project.read_project(self.path)[3],pins)
        self.assertEqual(report['authoredFrames'],8);self.assertEqual(report['periodMs'],680)
        self.assertEqual(report['temporalReview'],'UNREVIEWED');self.assertFalse(report['visualApproval'])
        self.assertFalse(report['frameAudit']['lastEqualsFirst'])
        self.assertEqual(sum(report['encodedGifTiming']['native']['durationsMs']),680)
        with self.assertRaises(ValueError):project.export_project(self.path,out)
    def test_all_protected_pixels_and_integer_shared_head(self):
        p,frames,bodies,heads=project.render_frames(self.path)
        with Image.open(self.path.parent/p['sharedHead']) as original_head: head=original_head.copy()
        for row,frame,body,moved_head in zip(p['frames'],frames,bodies,heads):
            with Image.open(self.path.parent/row['body']) as source:
                np.testing.assert_array_equal(np.array(source)[row['lockY']:],np.array(frame)[row['lockY']:])
            expected=Image.new('RGBA',head.size);expected.alpha_composite(head,tuple(row['headTranslation']))
            np.testing.assert_array_equal(moved_head,expected)
        self.assertEqual(project.axis_summary([r['targetLandmarks'][0] for r in p['frames']], p['durationsMs'])['halfCycleMaxDifference'],[0.,0.])
    def test_source_tamper_fails_until_explicit_repin(self):
        source=self.path.parent/'body-000.png';image=Image.open(source);image.putpixel((1,1),(1,2,3,255));image.save(source)
        with self.assertRaisesRegex(ValueError,'stale'):project.read_project(self.path)
        project.pin_project(self.path);project.read_project(self.path)
    def test_export_tamper_detected(self):
        out=self.root/'rendered';project.export_project(self.path,out)
        (out/'frame-000.png').write_bytes(b'not a frame')
        result=project.verify_export(self.path,out)
        self.assertFalse(result['byteExact']);self.assertIn('frame-000.png',result['mismatches'])
    def test_noninteger_head_translation_rejected(self):
        self.update(lambda p:p['frames'][0].update(headTranslation=[.2,0]))
        with self.assertRaisesRegex(ValueError,'integers'):project.read_project(self.path)
    def test_paths_dimensions_and_timing_are_explicit(self):
        self.update(lambda p:p.update(sharedHead='../elsewhere.png'))
        with self.assertRaisesRegex(ValueError,'inside'):project.read_project(self.path)
        self.path=project.create_demo(self.root/'other')
        self.update(lambda p:p.update(durationsMs=[83]*8))
        with self.assertRaisesRegex(ValueError,'duration'):project.read_project(self.path)
    def test_insufficient_landmarks_rejected(self):
        self.update(lambda p:p['frames'][0].update(sourceLandmarks=[[0,1],[0,2]]))
        with self.assertRaisesRegex(ValueError,'three'):project.read_project(self.path)
    def test_head_cannot_cross_protected_region(self):
        self.update(lambda p:p['frames'][0].update(headTranslation=[0,90]))
        with self.assertRaisesRegex(ValueError,'protected'):project.render_frames(self.path)
    def test_axis_summary_includes_last_to_first(self):
        self.assertEqual(project.axis_summary([[0,0],[1,2],[3,4],[7,8]])['maxAdjacentXYStepIncludingLoop'],[7.,8.])
    def test_half_cycle_summary_requires_matching_hold_timelines(self):
        points=[[0,0],[1,1],[0,0],[1,1]]
        unequal=project.axis_summary(points,[10,20,20,10])
        self.assertEqual(unequal['halfFrameCountOffsetMaxDifference'],[0.,0.])
        self.assertIsNone(unequal['halfCycleMaxDifference']);self.assertFalse(unequal['halfCycleTimingMatched'])
        self.assertEqual(project.axis_summary(points,[10,20,10,20])['halfCycleMaxDifference'],[0.,0.])
    def test_clipped_head_is_reported_not_silently_certified(self):
        self.update(lambda p:p['frames'][0].update(headTranslation=[500,0]))
        report=project.export_project(self.path,self.root/'clipped')
        self.assertTrue(report['canvasWarnings'][0]['sharedHeadWouldBeClipped']);self.assertFalse(report['visualApproval'])
    def test_gif_period_limit_fails_before_output_writes(self):
        def extend(p):
            p['frames']=[p['frames'][0]]*12;p['durationsMs']=[60000]*12
        self.update(extend)
        with self.assertRaisesRegex(ValueError,'single-hold'):
            project.export_project(self.path,self.root/'too-long')
        self.assertFalse((self.root/'too-long').exists())
    def test_demo_never_overwrites_source(self):
        before=self.path.read_bytes()
        with self.assertRaises(ValueError):project.create_demo(self.path.parent)
        self.assertEqual(self.path.read_bytes(),before)

if __name__=='__main__':unittest.main()
