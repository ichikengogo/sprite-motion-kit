import hashlib
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import production_audit as audit

class ProductionAuditTests(unittest.TestCase):
    def test_contour_pixel_omission_and_overlap_are_separate(self):
        source = Image.new('RGBA',(3,3),(20,30,40,255)); source.putpixel((0,0),(20,30,40,1))
        a=source.copy(); a.putpixel((0,0),(0,0,0,0))
        report, overlay=audit.ownership_report(source,{'a':a,'b':a})
        self.assertEqual(report['omittedSourcePixels'],1); self.assertEqual(report['overlapPixels'],8)
        self.assertEqual(overlay.getpixel((0,0)),(255,0,255,255)); self.assertFalse(report['visualApproval'])
    def test_tracks_use_variable_duration_and_wrap(self):
        row=audit.audit_tracks({'sole':[[0,0],[2,0],[2,1]]},[100,500,200])['tracks']['sole']
        self.assertEqual(row['speedPixelsPerSecond'][:2],[20,2])
        self.assertAlmostEqual(row['lastToFirstSpeed'],5*(5**0.5))
    def test_tracks_reject_invalid_time_or_nonfinite(self):
        for duration in ([10,0,10],[10,True,10],[10,float('nan'),10]):
            with self.assertRaises(ValueError):audit.audit_tracks({'p':[[0,0]]*3},duration)
        with self.assertRaises(ValueError):audit.audit_tracks({'p':[[float('nan'),0]]*3},[10]*3)
    def test_repeated_endpoint_is_diagnostic_not_approval(self):
        with tempfile.TemporaryDirectory() as td:
            paths=[]
            for i,c in enumerate(('red','blue','red')):
                p=Path(td)/f'frame-{i:03}.png';Image.new('RGBA',(3,3),c).save(p);paths.append(p)
            r=audit.audit_frames(paths,[100]*3)
            self.assertTrue(r['lastEqualsFirst']);self.assertEqual(r['adjacentIdenticalIndices'],[2]);self.assertFalse(r['visualApproval'])
    def test_temporal_claim_requires_fresh_actual_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'preview.gif';p.write_bytes(b'fixture bytes, not playback evidence')
            r={'reviewer':None,'methodTool':None,'artifactSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'speed':None,'nativeCompleteLoopsObserved':None,'smallCompleteLoopsObserved':None,'smallSizePx':128,'continuityFindings':None,'outcome':'unreviewed','unresolvedDefects':[]}
            self.assertFalse(audit.validate_temporal_record(r,p)['playbackIndependentlyVerified'])
            r['outcome']='accepted'
            with self.assertRaises(ValueError):audit.validate_temporal_record(r,p)
            r.update(reviewer='test assertion',methodTool='test only',speed=1,nativeCompleteLoopsObserved=2,smallCompleteLoopsObserved=2,continuityFindings='test of schema, not actual review')
            self.assertFalse(audit.validate_temporal_record(r,p)['visualApproval'])
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):audit.validate_temporal_record(r,p)
if __name__=='__main__':unittest.main()
