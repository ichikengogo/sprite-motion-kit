"""Original geometric fixtures only; no character artwork or private calibration."""
import tempfile
import io
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from continuity_audit import backing_preservation, demo, registered_region
from repair_audit import audit


class ContinuityAuditTests(unittest.TestCase):
    def setUp(self):
        self.source = Image.new('RGBA', (32, 32))
        ImageDraw.Draw(self.source).rectangle((10, 6, 15, 24), fill=(60, 80, 100, 255))
        self.mask = self.source.getchannel('A')

    def test_integer_bob_keeps_core_without_refitting(self):
        for dy in (0, 2, 0, -2, 0, 2, 0, -2):
            moved = Image.new('RGBA', self.source.size)
            moved.alpha_composite(self.source, (0, dy))
            report = registered_region(self.source, moved, self.mask, (0, dy))
            self.assertTrue(report['matches'])
            self.assertFalse(report['visualApproval'])
            self.assertEqual(report['temporalReview'], 'UNREVIEWED')

    def test_wrong_bob_or_lateral_drift_is_not_registered_away(self):
        moved = Image.new('RGBA', self.source.size)
        moved.alpha_composite(self.source, (1, 2))
        self.assertFalse(registered_region(self.source, moved, self.mask, (0, 2))['matches'])

    def test_core_equality_does_not_check_face_direction(self):
        # An identically wrong reference still matches: semantic inspection is separate.
        report = registered_region(self.source, self.source, self.mask)
        self.assertTrue(report['matches'])
        self.assertFalse(report['visualApproval'])

    def test_whole_strap_not_just_buckle_core(self):
        missing = self.source.copy()
        ImageDraw.Draw(missing).rectangle((10, 15, 15, 24), fill=(0, 0, 0, 0))
        buckle = Image.new('L', self.source.size)
        ImageDraw.Draw(buckle).rectangle((10, 6, 15, 10), fill=255)
        self.assertTrue(registered_region(self.source, missing, buckle)['matches'])
        report = registered_region(self.source, missing, self.mask)
        self.assertEqual(report['missingTransparentPixels'], 60)
        self.assertFalse(report['matches'])

    def test_occlusion_has_candidate_coordinates_and_independent_owner(self):
        moved = Image.new('RGBA', self.source.size)
        moved.alpha_composite(self.source, (0, 2))
        hand = Image.new('RGBA', self.source.size)
        ImageDraw.Draw(hand).rectangle((8, 12, 18, 17), fill=(180, 130, 100, 255))
        composite = Image.alpha_composite(moved, hand)
        report = registered_region(self.source, composite, self.mask, (0, 2), hand.getchannel('A'))
        self.assertTrue(report['matches'])
        self.assertEqual(report['occludedPixels'], 36)
        self.assertTrue(registered_region(hand, composite, hand.getchannel('A'))['matches'])
        # Wrong draw order can pass the hidden strap check but fails foreground ownership.
        wrong = Image.alpha_composite(hand, moved)
        self.assertTrue(registered_region(self.source, wrong, self.mask, (0, 2), hand.getchannel('A'))['matches'])
        self.assertFalse(registered_region(hand, wrong, hand.getchannel('A'))['matches'])

    def test_fully_occluded_is_unmeasured_not_a_pass(self):
        report = registered_region(self.source, Image.new('RGBA', (32, 32)), self.mask,
                                   occluder_mask=Image.new('L', (32, 32), 255))
        self.assertIsNone(report['matches'])
        self.assertEqual(report['measurementStatus'], 'FULLY_OCCLUDED')

    def test_missing_fist_and_opaque_white_are_distinct(self):
        hole = self.source.copy()
        hole.putpixel((12, 10), (255, 255, 255, 0))
        white = self.source.copy()
        white.putpixel((12, 10), (255, 255, 255, 255))
        partial = self.source.copy()
        partial.putpixel((12, 10), (60, 80, 100, 127))
        reports = [registered_region(self.source, image, self.mask) for image in (hole, white, partial)]
        self.assertEqual([r['missingTransparentPixels'] for r in reports], [1, 0, 0])
        self.assertEqual([r['changedOpaquePixels'] for r in reports], [0, 1, 0])
        self.assertEqual([r['partialAlphaPixels'] for r in reports], [0, 0, 1])

    def test_white_is_not_intrinsically_a_defect(self):
        white = Image.new('RGBA', (32, 32), 'white')
        self.assertTrue(registered_region(white, white, self.mask)['matches'])

    def test_complete_hand_mass_disappears_while_sleeve_remains(self):
        arm = Image.new('RGBA', (32, 32))
        ImageDraw.Draw(arm).rectangle((10, 6, 14, 17), fill=(60, 80, 100, 255))
        ImageDraw.Draw(arm).rectangle((9, 18, 16, 23), fill=(180, 130, 100, 255))
        hand = Image.new('L', arm.size)
        ImageDraw.Draw(hand).rectangle((9, 18, 16, 23), fill=255)
        candidates = [arm.copy() for _ in range(8)]
        ImageDraw.Draw(candidates[5]).rectangle((9, 18, 16, 23), fill=(0, 0, 0, 0))
        reports = [registered_region(arm, frame, hand) for frame in candidates]
        self.assertEqual([r['matches'] for r in reports], [True] * 5 + [False, True, True])
        self.assertEqual(reports[5]['missingTransparentPixels'], 48)
        self.assertEqual(arm.crop((10, 6, 15, 18)).tobytes(),
                         candidates[5].crop((10, 6, 15, 18)).tobytes())

    def test_encoded_animation_is_rejected(self):
        stream = io.BytesIO()
        first = Image.new('RGBA', (32, 32), 'red')
        first.save(stream, format='GIF', save_all=True,
                   append_images=[Image.new('RGBA', (32, 32), 'blue')], duration=100)
        stream.seek(0)
        with Image.open(stream) as animation:
            with self.assertRaises(ValueError):
                registered_region(self.source, animation, self.mask)
            with self.assertRaises(ValueError):
                backing_preservation(animation, self.source, self.mask)

    def test_backing_invalid_canvas_and_scope(self):
        with self.assertRaises(ValueError):
            backing_preservation(self.source, Image.new('RGBA', (16, 16)), self.mask)
        for mask in (Image.new('L', (32, 32)), Image.new('L', (32, 32), 128),
                     Image.new('L', (16, 16), 255), Image.new('RGB', (32, 32))):
            with self.subTest(mode=mask.mode, size=mask.size), self.assertRaises(ValueError):
                backing_preservation(self.source, self.source, mask)

    def test_clipping_is_rejected_not_wrapped_or_ignored(self):
        for offset in ((0, 30), (-20, 0), (10**30, 0)):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                registered_region(self.source, self.source, self.mask, offset)

    def test_invalid_offsets(self):
        for offset in ((0.0, 0), (False, 0), (1,), '1,2'):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                registered_region(self.source, self.source, self.mask, offset)

    def test_invalid_region_masks(self):
        for mask in (Image.new('L', (32, 32)), Image.new('L', (32, 32), 128),
                     Image.new('RGB', (32, 32)), Image.new('L', (16, 16), 255),
                     Image.new('L', (32, 32), 255)):
            with self.subTest(mode=mask.mode, size=mask.size), self.assertRaises(ValueError):
                registered_region(self.source, self.source, mask)

    def test_invalid_candidate_or_occluder(self):
        with self.assertRaises(ValueError):
            registered_region(self.source, Image.new('RGBA', (16, 16)), self.mask)
        with self.assertRaises(ValueError):
            registered_region(self.source, self.source, self.mask,
                              occluder_mask=Image.new('L', (32, 32), 128))
        with self.assertRaises(ValueError):
            registered_region(None, self.source, self.mask)

    def test_inputs_not_mutated_and_hashes_bind_masks(self):
        snapshot = self.source.tobytes(), self.mask.tobytes()
        first = registered_region(self.source, self.source, self.mask)
        mask = self.mask.copy()
        mask.putpixel((10, 6), 0)
        second = registered_region(self.source, self.source, mask)
        self.assertNotEqual(first['inputs']['regionMask'], second['inputs']['regionMask'])
        self.assertEqual(snapshot, (self.source.tobytes(), self.mask.tobytes()))

    def test_hair_backing_preserves_opaque_foreground_and_negative_space(self):
        scope = Image.new('L', self.source.size)
        ImageDraw.Draw(scope).rectangle((8, 10, 17, 22), fill=255)
        backing = Image.new('RGBA', self.source.size)
        ImageDraw.Draw(backing).rectangle((8, 10, 17, 22), fill=(90, 50, 30, 255))
        result = Image.alpha_composite(backing, self.source)
        report = backing_preservation(self.source, result, scope)
        self.assertTrue(report['invariantsPass'])
        self.assertGreater(report['gainedAlphaPixels'], 0)
        self.assertEqual(result.getpixel((5, 10))[3], 0)

    def test_backing_cannot_paint_over_opaque_hand(self):
        wrong = self.source.copy()
        wrong.putpixel((12, 10), (255, 255, 255, 255))
        report = backing_preservation(self.source, wrong, self.mask)
        self.assertFalse(report['invariantsPass'])
        self.assertEqual(report['opaqueForegroundChangedPixels'], 1)

    def test_backing_detects_alpha_loss_and_outside_scope(self):
        wrong = self.source.copy()
        wrong.putpixel((12, 10), (0, 0, 0, 0))
        wrong.putpixel((1, 1), (90, 50, 30, 255))
        report = backing_preservation(self.source, wrong, self.mask)
        self.assertEqual(report['alphaDecreasedPixels'], 1)
        self.assertEqual(report['outsideAllowedPixels'], 1)
        self.assertFalse(report['invariantsPass'])

    def test_partial_foreground_may_composite_with_backing(self):
        before = self.source.copy()
        before.putpixel((12, 10), (60, 80, 100, 128))
        report = backing_preservation(before, self.source, self.mask)
        self.assertTrue(report['invariantsPass'])
        self.assertEqual(report['gainedAlphaPixels'], 1)

    def test_unchanged_backing_pass_is_not_a_claim_hole_was_filled(self):
        report = backing_preservation(self.source, self.source, self.mask)
        self.assertTrue(report['invariantsPass'])
        self.assertEqual(report['gainedAlphaPixels'], 0)
        self.assertFalse(report['visualApproval'])

    def test_tip_repair_keeps_lower_component_and_other_phases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('before', 'after', 'masks'):
                (root / name).mkdir()
            for index in range(4):
                before = self.source.copy()
                before.putpixel((16, 6), (60, 80, 100, 255))
                after = before.copy()
                scope = Image.new('L', self.source.size)
                if index in (0, 3):
                    after.putpixel((16, 6), (0, 0, 0, 0))
                    scope.putpixel((16, 6), 255)
                for folder, image in [('before', before), ('after', after), ('masks', scope)]:
                    image.save(root / folder / f'frame-{index:03}.png')
                self.assertTrue(registered_region(self.source, after, self.mask)['matches'])
            report = audit(root / 'before', root / 'after', root / 'masks')
            self.assertTrue(report['invariantsPass'])
            self.assertEqual([row['changedPixels'] for row in report['frames']], [1, 0, 0, 1])

    def test_demo_reproduces_original_fixtures_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / 'first', Path(directory) / 'second'
            report = demo(first)
            self.assertTrue(report['expectedResultsObserved'])
            demo(second)
            for path in first.iterdir():
                self.assertEqual(path.read_bytes(), (second / path.name).read_bytes())
            with self.assertRaises(ValueError):
                demo(first)


if __name__ == '__main__':
    unittest.main()
