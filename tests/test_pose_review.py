"""Structure/geometry regressions only: these tests do NOT observe palm or playback."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, PngImagePlugin

import pose_review as review


class PoseReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        review.demo(self.root)
        self.manifest = json.loads((self.root / 'manifest.json').read_text())
        self.worksheet = json.loads((self.root / 'review.json').read_text())

    def tearDown(self):
        self.temp.cleanup()

    def check(self, **kwargs):
        return review.check_review(self.manifest, self.worksheet, self.root, **kwargs)

    def record(self, row=None, visibility='unknown'):
        row = self.worksheet['rows'][0] if row is None else row
        row.update(reviewStatus='RECORDED', reviewer='Synthetic schema test',
                   findings='Authored test assertion, not actual visual review.')
        row['observed']['visibility'] = visibility
        return row

    def landmarks(self):
        return {'reviewer': 'Synthetic geometry test', 'pelvis': [48, 50],
                'arms': {'arm-A': {'shoulder': [10, 10], 'elbow': [20, 10], 'wrist': [20, 20],
                                  'handMaskPixels': [[20, 20], [21, 20], [20, 21], [21, 21]]}},
                'legs': {'leg-A': {'phase': 'support', 'hip': [48, 50],
                                   'knee': [48, 65], 'ankle': [48, 80]}}}

    def test_init_covers_all_actual_frames_physical_arms_and_phases(self):
        self.assertEqual(len(self.worksheet['rows']), 6)
        self.assertEqual({row['phase'] for row in self.worksheet['rows']}, {'start', 'middle', 'end'})
        report = self.check()
        self.assertTrue(report['schemaValid'])
        self.assertTrue(report['coverageComplete'])
        self.assertTrue(report['sourceSetFresh'])
        self.assertEqual(report['durationMs'], 340)
        self.assertEqual(report['authoredFrameCount'], 3)
        self.assertIsNone(report['encodedFrameCount'])
        self.assertFalse(report['reviewRecordsComplete'])
        self.assertTrue(report['checkPassed'])
        self.assertFalse(self.check(require_recorded=True)['checkPassed'])
        self.assertTrue(all(row['reviewStatus'] == 'UNREVIEWED' for row in self.worksheet['rows']))
        self.assertTrue(all(row['expected'] == review.unknown_semantics() for row in self.worksheet['rows']))

    def test_single_view_is_enough_order_and_real_durations_are_preserved(self):
        self.manifest['view'] = 'side'
        self.manifest['facing'] = 'left'
        self.manifest['frames'].reverse()
        self.manifest['frames'][0]['durationMs'] = 35.5
        worksheet = review.init_review(self.manifest, self.root)
        self.assertEqual([r['frameId'] for r in worksheet['rows']][::2], ['cel-2', 'cel-1', 'cel-0'])
        self.assertEqual(worksheet['snapshot']['manifest']['frames'][0]['durationMs'], 35.5)
        self.assertTrue(review.check_review(self.manifest, worksheet, self.root)['checkPassed'])

    def test_hold_paths_allowed_but_frame_ids_cannot_duplicate(self):
        self.manifest['frames'][1]['path'] = self.manifest['frames'][0]['path']
        self.assertEqual(len(review.init_review(self.manifest, self.root)['rows']), 6)
        self.manifest['frames'][1]['id'] = self.manifest['frames'][0]['id']
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            review.init_review(self.manifest, self.root)

    def test_every_original_and_actual_cel_invalidates_all_recorded_rows(self):
        self.record()
        for name in ['source.png', 'frame-000.png', 'frame-001.png', 'frame-002.png']:
            with self.subTest(name=name):
                self.worksheet = review.init_review(self.manifest, self.root)
                for row in self.worksheet['rows']:
                    self.record(row)
                with Image.open(self.root / name) as image:
                    changed = image.convert('RGBA')
                changed.putpixel((0, 0), (3, 5, 7, 255))
                changed.save(self.root / name)
                report = self.check(require_recorded=True)
                self.assertFalse(report['sourceSetFresh'])
                self.assertEqual(len(report['staleRecordedRows']), 6)
                self.assertFalse(report['reviewRecordsComplete'])
                self.assertFalse(report['checkPassed'])

    def test_byte_changes_are_stale_even_if_rgba_pixels_match(self):
        self.record()
        path = self.root / 'source.png'
        with Image.open(path) as image:
            same_pixels = image.copy()
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('description', 'Synthetic metadata change')
        same_pixels.save(path, pnginfo=metadata)
        self.assertFalse(self.check()['sourceSetFresh'])

    def test_context_changes_invalidate_snapshot(self):
        original = copy.deepcopy(self.manifest)
        for change in ('duration', 'phase', 'mapping', 'scale', 'order', 'facing'):
            with self.subTest(change=change):
                self.manifest = copy.deepcopy(original)
                if change == 'duration': self.manifest['frames'][0]['durationMs'] += 1
                if change == 'phase': self.manifest['frames'][0]['phase'] = 'exchange'
                if change == 'mapping': self.manifest['frames'][0]['armMapping']['arm-A']['nearFar'] = 'near'
                if change == 'scale': self.manifest['fixedScale'] = 2
                if change == 'order': self.manifest['frames'].reverse()
                if change == 'facing': self.manifest['facing'] = 'away'
                self.assertFalse(self.check()['sourceSetFresh'])

    def test_new_manifest_frame_reports_stale_and_missing_current_coverage(self):
        frame = copy.deepcopy(self.manifest['frames'][0])
        frame['id'] = 'new-phase'
        frame['phase'] = 'exchange'
        self.manifest['frames'].append(frame)
        report = self.check()
        self.assertFalse(report['sourceSetFresh'])
        self.assertFalse(report['coverageComplete'])
        self.assertEqual(report['missingCurrentRows'], [['new-phase', 'arm-A'], ['new-phase', 'arm-B']])

    def test_missing_arm_and_omitted_phase_rows_fail(self):
        original = copy.deepcopy(self.worksheet)
        for rows in (original['rows'][:-1], [r for r in original['rows'] if r['phase'] != 'middle']):
            with self.subTest(rows=len(rows)):
                self.worksheet = copy.deepcopy(original)
                self.worksheet['rows'] = rows
                with self.assertRaisesRegex(ValueError, 'Missing'):
                    self.check()

    def test_duplicate_rows_or_changed_bound_mapping_fail(self):
        self.worksheet['rows'].append(copy.deepcopy(self.worksheet['rows'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.check()
        self.worksheet['rows'].pop()
        self.worksheet['rows'][0]['mapping']['nearFar'] = 'near'
        # A stale source must not disable validation against the original binding.
        self.manifest['frames'][0]['durationMs'] += 1
        with self.assertRaisesRegex(ValueError, 'phase/mapping'):
            self.check()

    def test_missing_frame_mapping_blank_phase_and_duplicate_arms_fail(self):
        original = copy.deepcopy(self.manifest)
        for change in ('mapping', 'phase', 'arms'):
            self.manifest = copy.deepcopy(original)
            if change == 'mapping': del self.manifest['frames'][0]['armMapping']['arm-B']
            if change == 'phase': self.manifest['frames'][0]['phase'] = ' '
            if change == 'arms': self.manifest['physicalArms'].append(copy.deepcopy(self.manifest['physicalArms'][0]))
            with self.subTest(change=change), self.assertRaises(ValueError):
                review.init_review(self.manifest, self.root)

    def test_invalid_durations_and_fixed_scale_fail(self):
        for field in ('durationMs', 'fixedScale'):
            for value in (0, -1, True, '100', float('nan'), float('inf'), 10**1000):
                manifest = copy.deepcopy(self.manifest)
                target = manifest['frames'][0] if field == 'durationMs' else manifest
                target[field] = value
                with self.subTest(field=field, value=str(value)[:25]), self.assertRaises(ValueError):
                    review.init_review(manifest, self.root)

    def test_original_native_dimensions_preserved_but_frames_fixed(self):
        Image.new('RGBA', (48, 72), 'red').save(self.root / 'source.png')
        worksheet = review.init_review(self.manifest, self.root)
        self.assertEqual(worksheet['snapshot']['files'][0]['canvas'], [48, 72])
        self.assertTrue(review.check_review(self.manifest, worksheet, self.root)['sourceSetFresh'])
        Image.new('RGBA', (48, 72), 'blue').save(self.root / 'frame-000.png')
        with self.assertRaisesRegex(ValueError, 'Fixed canvas'):
            review.init_review(self.manifest, self.root)

    def test_encoded_animation_is_not_an_authored_frame(self):
        Image.new('RGBA', (96, 96), 'red').save(self.root / 'frame-000.png', save_all=True,
            append_images=[Image.new('RGBA', (96, 96), 'blue')], duration=[100, 100], loop=0)
        with self.assertRaisesRegex(ValueError, 'single-frame PNG'):
            review.init_review(self.manifest, self.root)

    def test_expected_is_not_promoted_to_observed_and_no_universal_palm_rule(self):
        row = self.worksheet['rows'][0]
        row['expected'].update(visibility='visible', surface='back', thumbSide='away-from-body',
                               thumbTip='not-visible', fistUpRelativeToWrist='no', forwardThrust='yes')
        self.assertEqual(row['observed'], review.unknown_semantics())
        self.assertTrue(self.check()['checkPassed'])
        self.record(row, visibility='visible')
        row['observed'].update(surface='back', thumbSide='away-from-body', thumbTip='not-visible',
                               fistUpRelativeToWrist='no', forwardThrust='yes')
        report = self.check()
        self.assertEqual(report['authoredAssertionDifferences'], [])
        self.assertFalse(report['visualApproval'])

    def test_occluded_or_unknown_cannot_assert_visible_surface(self):
        row = self.record()
        for visibility in ('unknown', 'occluded'):
            for field, value in [('surface', 'palm'), ('thumbSide', 'toward-body'), ('fingers', 'coherent')]:
                row['observed'] = review.unknown_semantics()
                row['observed'].update(visibility=visibility, **{field: value})
                with self.subTest(visibility=visibility, field=field), self.assertRaisesRegex(ValueError, 'contradict'):
                    self.check()

    def test_partial_visibility_preserves_unknown_and_occluded_without_acceptance(self):
        row = self.record(visibility='partial')
        row['observed'].update(surface='edge', thumbSide='occluded', thumbTip='not-visible')
        report = self.check()
        self.assertEqual(report['unresolvedAssertions'][0]['observedOccluded'], ['thumbSide'])
        self.assertFalse(report['automaticSemanticValidation'])
        row['observed']['visibility'] = 'visible'
        with self.assertRaisesRegex(ValueError, 'contradicts occluded'):
            self.check()

    def test_expected_occlusion_is_reported_and_known_visibility_disagreement_surfaces(self):
        row = self.record(visibility='visible')
        row['expected'].update({key: 'occluded' for key in review.SEMANTIC_CHOICES})
        row['observed']['surface'] = 'palm'
        report = self.check()
        difference = report['authoredAssertionDifferences'][0]['fields']['visibility']
        self.assertEqual(difference, {'expected': 'occluded', 'observed': 'visible'})
        self.assertIn('surface', report['unresolvedAssertions'][0]['expectedOccluded'])
        self.assertIn('structure', report['checkScope'])

    def test_body_relative_up_requires_authored_reference(self):
        row = self.record(visibility='visible')
        row['observed']['fistUpRelativeToBody'] = 'yes'
        with self.assertRaisesRegex(ValueError, 'bodyReference'):
            self.check()
        row['observed']['bodyReference'] = 'Up along the authored torso axis from pelvis to chest.'
        self.assertTrue(self.check()['checkPassed'])

    def test_unreviewed_cannot_hide_claims_and_recorded_needs_evidence(self):
        row = self.worksheet['rows'][0]
        row['observed']['visibility'] = 'visible'
        with self.assertRaisesRegex(ValueError, 'UNREVIEWED'):
            self.check()
        self.record(row)
        for field in ('reviewer', 'findings'):
            previous = row[field]
            row[field] = ' '
            with self.assertRaisesRegex(ValueError, field):
                self.check()
            row[field] = previous
        row['observed']['surface'] = 'always-palm'
        with self.assertRaisesRegex(ValueError, 'surface'):
            self.check()

    def test_schema_pass_never_certifies_semantics_or_playback(self):
        for row in self.worksheet['rows']:
            self.record(row)
        first = self.worksheet['rows'][0]
        first['expected'].update(visibility='visible', surface='palm')
        first['observed'].update(visibility='visible', surface='back')
        report = self.check(require_recorded=True)
        self.assertTrue(report['checkPassed'])
        self.assertTrue(report['reviewRecordsComplete'])
        self.assertFalse(report['visualApproval'])
        self.assertFalse(report['playbackIndependentlyVerified'])
        self.assertFalse(report['automaticSemanticValidation'])
        self.assertEqual(report['temporalReview'], 'UNREVIEWED')
        self.assertTrue(report['unresolvedAssertions'])
        self.assertEqual(report['authoredAssertionDifferences'][0]['fields']['surface'],
                         {'expected': 'palm', 'observed': 'back'})
        for field, value in [('visualApproval', True), ('temporalReview', 'REVIEWED')]:
            original = self.worksheet[field]
            self.worksheet[field] = value
            with self.assertRaisesRegex(ValueError, 'cannot assert'):
                self.check()
            self.worksheet[field] = original

    def test_snapshot_hash_and_file_inventory_cannot_be_silently_edited(self):
        self.worksheet['snapshot']['files'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'digest'):
            self.check()
        self.worksheet = review.init_review(self.manifest, self.root)
        self.worksheet['snapshot']['files'].pop()
        with self.assertRaisesRegex(ValueError, 'every source'):
            self.check()

    def test_landmark_diagnostics_lengths_mask_wrist_and_declared_support(self):
        record = self.landmarks()
        self.worksheet['landmarks']['cel-0'] = record
        measured = self.check()['landmarkDiagnostics']['cel-0']
        arm = measured['arms']['arm-A']
        self.assertEqual([arm['upperArmPixels'], arm['forearmPixels']], [10, 10])
        self.assertEqual(arm['handMask']['areaPixels'], 4)
        self.assertEqual(arm['handMask']['boundsExclusive'], [20, 20, 22, 22])
        self.assertEqual(arm['handMask']['centroid'], [21, 21])
        self.assertEqual(arm['handMask']['centroidFromWrist'], [1, 1])
        self.assertEqual(measured['pelvisY'], 50)
        leg = measured['legs']['leg-A']
        self.assertEqual(leg['hipKneeAnkleDegrees'], 180)
        self.assertEqual(leg['hipAnkleReachPixels'], 30)
        self.assertEqual(leg['reachOverSegmentSum'], 1)
        self.assertEqual(leg['declaredPhase'], 'support')
        record['legs']['leg-A']['phase'] = 'recovery'
        self.assertEqual(self.check()['landmarkDiagnostics']['cel-0']['legs']['leg-A']['declaredPhase'], 'recovery')
        record['legs']['leg-A']['phase'] = 'unknown'
        self.assertFalse(self.check()['landmarkDiagnostics']['cel-0']['automaticSupportInference'])
        self.assertFalse(self.check()['visualApproval'])

    def test_landmark_geometry_rejects_nonfinite_bool_degenerate_and_unknown_phases(self):
        for value in ([float('nan'), 0], [0, float('inf')], [True, 10], [-1, 0], [97, 0], [10]):
            record = self.landmarks()
            record['pelvis'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                review.landmark_diagnostics(record, [96, 96], ['arm-A'])
        for part, key in [('arms', 'arm-A'), ('legs', 'leg-A')]:
            record = self.landmarks()
            fields = ('shoulder', 'elbow') if part == 'arms' else ('hip', 'knee')
            record[part][key][fields[1]] = record[part][key][fields[0]][:]
            with self.subTest(part=part), self.assertRaisesRegex(ValueError, 'Degenerate'):
                review.landmark_diagnostics(record, [96, 96], ['arm-A'])
        record = self.landmarks()
        record['legs']['leg-A']['phase'] = 'automatic-support'
        with self.assertRaisesRegex(ValueError, 'declared leg phase'):
            review.landmark_diagnostics(record, [96, 96], ['arm-A'])

    def test_hand_mask_is_explicit_nonempty_unique_integer_pixels(self):
        for pixels in ([], [[1, 1], [1, 1]], [[1.5, 2]], [[False, 2]], [[96, 2]]):
            record = self.landmarks()
            record['arms']['arm-A']['handMaskPixels'] = pixels
            with self.subTest(pixels=pixels), self.assertRaises(ValueError):
                review.landmark_diagnostics(record, [96, 96], ['arm-A'])

    def test_stale_landmarks_withheld_and_missing_measurements_are_not_zero(self):
        self.assertEqual(self.check()['landmarkDiagnostics'], {})
        self.worksheet['landmarks']['cel-0'] = self.landmarks()
        self.manifest['frames'][0]['durationMs'] += 1
        self.assertIsNone(self.check()['landmarkDiagnostics'])
        del self.worksheet['landmarks']['cel-1']
        with self.assertRaisesRegex(ValueError, 'every actual frame'):
            self.check()

    def test_path_escape_absolute_and_symlink_are_rejected(self):
        for path in ('../outside.png', str(self.root / 'source.png')):
            with self.subTest(path=path), self.assertRaises(ValueError):
                review.confined_path(self.root, path)
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / 'outside.png'
            Image.new('RGBA', (96, 96), 'red').save(outside)
            (self.root / 'escape.png').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'escapes'):
                review.confined_path(self.root, 'escape.png')

    def test_cli_checks_does_not_overwrite_inputs_or_follow_output_alias(self):
        source_bytes = (self.root / 'source.png').read_bytes()
        (self.root / 'source-alias.png').symlink_to(self.root / 'source.png')
        base = ['--root', str(self.root), 'check', 'manifest.json', 'review.json']
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.main(base), 0)
            self.assertEqual(review.main(base + ['--require-recorded']), 1)
            for path in ('source.png', 'source-alias.png', 'manifest.json', 'review.json'):
                self.assertEqual(review.main(base + ['--out', path]), 1)
            self.assertEqual(review.main(base + ['--out', 'check.json']), 0)
            self.assertEqual(review.main(['--root', str(self.root), 'demo']), 1)
            self.assertEqual(review.main(['--root', str(self.root), 'init', 'manifest.json', 'review.json']), 1)
            self.assertEqual(review.main(['--root', str(self.root), 'init', 'manifest.json', 'new-review.json']), 0)
        self.assertEqual((self.root / 'source.png').read_bytes(), source_bytes)
        self.assertFalse(json.loads((self.root / 'check.json').read_text())['visualApproval'])

    def test_tracked_sheet_has_one_scale_order_and_transparent_overflow(self):
        a = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
        b = a.copy()
        a.putpixel((0, 0), (255, 0, 0, 255))
        b.putpixel((4, 4), (0, 0, 255, 255))
        sheet = review.tracked_region_sheet([a, b], [[0, 0], [4, 4]], (4, 4), zoom=2, columns=2)
        self.assertEqual(sheet.size, (16, 8))
        self.assertEqual(sheet.getpixel((0, 0)), (0, 0, 0, 0))
        self.assertEqual(sheet.getpixel((4, 4)), (255, 0, 0, 255))
        self.assertEqual(sheet.getpixel((5, 5)), (255, 0, 0, 255))
        self.assertEqual(sheet.getpixel((12, 4)), (0, 0, 255, 255))
        self.assertEqual(sum(sheet.getpixel((x, y))[3] != 0 for y in range(sheet.height) for x in range(sheet.width)), 8)

    def test_tracked_sheet_rejects_rescale_and_invalid_anchors(self):
        a = Image.new('RGBA', (8, 8))
        invalid = [([a, Image.new('RGBA', (9, 8))], [[1, 1], [1, 1]], (4, 4), 2, 2),
                   ([a], [[1.5, 1]], (4, 4), 2, 2), ([a], [[True, 1]], (4, 4), 2, 2),
                   ([a], [[float('nan'), 1]], (4, 4), 2, 2), ([a], [[8, 1]], (4, 4), 2, 2),
                   ([a], [], (4, 4), 2, 2), ([a], [[1, 1]], (0, 4), 2, 2),
                   ([a], [[1, 1]], (4, 4), 1.5, 2), ([a], [[1, 1]], (4, 4), True, 2),
                   ([a], [[1, 1]], (4, 4), 2, 0)]
        for args in invalid:
            with self.subTest(args=str(args)[-60:]), self.assertRaises(ValueError):
                review.tracked_region_sheet(*args)


if __name__ == '__main__':
    unittest.main()
