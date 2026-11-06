"""Synthetic geometry only; assertions do not certify character art or motion."""
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw

from dash_registration import (
    ShapePreservingCubic, align_body_axis, axis_inverse_mapping, build_demo,
    cycle_frame_at, cycle_schedule, row_width_mapping, shaft_hand_mapping,
    translate_shared_layer, widen_rows,
)


class CubicTests(unittest.TestCase):
    def test_knots_shape_and_known_values(self):
        spline = ShapePreservingCubic([0, 1, 2], [0, 1, 4])
        np.testing.assert_array_equal(spline([0, 1, 2]), [0, 1, 4])
        self.assertEqual(spline(.5), .3125)
        self.assertEqual(spline(1.5), 2.1875)
        q = np.linspace(0, 2, 81).reshape(9, 9)
        self.assertEqual(spline(q).shape, q.shape)
        self.assertIsInstance(spline(.5), float)

    def test_monotone_no_overshoot_even_on_uneven_intervals(self):
        for values in ([0, .01, 9, 9, 9.1], [9.1, 9, 9, .01, 0]):
            x = [0, .05, .8, 3, 11]
            spline = ShapePreservingCubic(x, values)
            sign = 1 if values[-1] > values[0] else -1
            sampled = spline(np.linspace(0, 11, 10001))
            self.assertGreaterEqual(np.min(np.diff(sampled)*sign), -1e-12)
            for a, b, va, vb in zip(x, x[1:], values, values[1:]):
                q = spline(np.linspace(a, b, 101))
                self.assertGreaterEqual(q.min(), min(va, vb)-1e-12)
                self.assertLessEqual(q.max(), max(va, vb)+1e-12)

    def test_extrema_flat_regions_and_linear_two_points(self):
        np.testing.assert_allclose(ShapePreservingCubic([1, 4], [8, 2])([1, 2, 3, 4]), [8, 6, 4, 2])
        spline = ShapePreservingCubic([0, 1, 3, 5, 6], [2, 2, 5, -1, 0])
        for a, b, lo, hi in [(0, 1, 2, 2), (1, 3, 2, 5), (3, 5, -1, 5), (5, 6, -1, 0)]:
            values = spline(np.linspace(a, b, 101))
            self.assertGreaterEqual(values.min(), lo-1e-12)
            self.assertLessEqual(values.max(), hi+1e-12)

    def test_inputs_are_copied_and_invalids_rejected(self):
        x, y = np.array([0., 1.]), np.array([3., 7.])
        spline = ShapePreservingCubic(x, y)
        x[0] = 50; y[0] = -50
        self.assertEqual(spline(.5), 5)
        for xx, yy in [([0], [1]), ([0, 0], [1, 2]), ([2, 1], [1, 2]),
                       ([0, 1], [1]), ([[0, 1]], [[2, 3]]), ([0, float('nan')], [1, 2]),
                       ([0, 1], [1, float('inf')])]:
            with self.subTest(x=xx, y=yy), self.assertRaises(ValueError):
                ShapePreservingCubic(xx, yy)
        for q in (-.001, 1.001, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                spline(q)


class AxisTests(unittest.TestCase):
    def fixture(self, size=(73, 91)):
        rng = np.random.default_rng(204)
        return Image.fromarray(rng.integers(0, 256, (size[1], size[0], 4), dtype=np.uint8))

    def test_landmark_mapping_monotonic_and_clamped_regions(self):
        source = [[31, 11], [42, 34], [29, 52]]
        target = [[36, 13], [36, 30], [36, 54]]
        inv = axis_inverse_mapping(source, target, 67)
        np.testing.assert_allclose(inv(target), source, atol=1e-12)
        np.testing.assert_array_equal(inv([[0, 67], [36, 80], [73, 91]]), [[0, 67], [36, 80], [73, 91]])
        np.testing.assert_array_equal(inv([10, 3]), [5, 1])
        points = np.column_stack([np.full(10001, 36), np.linspace(0, 91, 10001)])
        self.assertGreater(np.min(np.diff(inv(points)[:, 1])), 0)
        np.testing.assert_allclose(inv([36, 67-1e-7]), [36, 67], atol=1e-6)

    def test_exact_lower_pixels_and_source_immutable(self):
        image = self.fixture()
        original = image.tobytes()
        source = [[31, 11], [42, 34], [29, 52]]
        target = [[36, 13], [36, 30], [36, 54]]
        landmarks = copy.deepcopy((source, target))
        repaired = align_body_axis(image, source, target, 67)
        self.assertEqual(repaired.size, (73, 91))
        self.assertEqual(repaired.crop((0, 67, 73, 91)).tobytes(), image.crop((0, 67, 73, 91)).tobytes())
        self.assertNotEqual(repaired.crop((0, 0, 73, 67)).tobytes(), image.crop((0, 0, 73, 67)).tobytes())
        self.assertEqual(original, image.tobytes())
        self.assertEqual((source, target), landmarks)

    def test_identity_is_exact_including_hidden_rgb_and_independent_copy(self):
        image = self.fixture()
        points = [[36, 11], [36, 34], [36, 52]]
        copy_image = align_body_axis(image, points, points, 91)
        self.assertIsNot(copy_image, image)
        self.assertEqual(image.tobytes(), copy_image.tobytes())
        copy_image.putpixel((0, 0), (0, 0, 0, 0))
        self.assertNotEqual(image.tobytes(), copy_image.tobytes())

    def test_mapping_has_own_copies_and_does_not_mutate_points(self):
        source = np.array([[31., 11.], [42., 34.], [29., 52.]])
        target = np.array([[36., 13.], [36., 30.], [36., 54.]])
        mapper = axis_inverse_mapping(source, target, 67)
        points = target.copy(); expected = source.copy()
        source[:] = 0; target[:] = 0
        np.testing.assert_allclose(mapper(points), expected)
        np.testing.assert_array_equal(points, [[36, 13], [36, 30], [36, 54]])

    def test_invalid_landmarks_modes_bounds_and_resampling(self):
        image = self.fixture()
        good = [[36, 11], [36, 34], [36, 52]]
        bad_cases = [([[36, 11]], [[36, 11]], 67),
                     ([[36, 11], [36, 11]], [[36, 11], [36, 34]], 67),
                     (good, [[36, 11], [37, 34], [36, 52]], 67),
                     (good, good[::-1], 67), (good, good, 52), (good, good, 92),
                     (good, good, 67.0), (good, good, True),
                     ([[36, -1], [36, 34], [36, 52]], good, 67),
                     ([[float('nan'), 11], [36, 34], [36, 52]], good, 67),
                     ([[74, 11], [36, 34], [36, 52]], good, 67)]
        for src, dst, lock in bad_cases:
            with self.subTest(src=src, dst=dst, lock=lock), self.assertRaises(ValueError):
                align_body_axis(image, src, dst, lock)
        with self.assertRaises(ValueError):
            align_body_axis(image.convert('RGB'), good, good, 67)
        with self.assertRaises(ValueError):
            align_body_axis(image, good, good, 67, resampling=Image.Resampling.LANCZOS)


class SharedLayerTests(unittest.TestCase):
    def test_every_copied_byte_preserved_without_alpha_blend(self):
        rng = np.random.default_rng(20)
        pixels = rng.integers(0, 256, (13, 17, 4), dtype=np.uint8)
        pixels[0, 0] = [120, 90, 30, 0]
        image = Image.fromarray(pixels)
        moved = np.asarray(translate_shared_layer(image, (3, -2)))
        np.testing.assert_array_equal(moved[:11, 3:], pixels[2:, :14])
        self.assertFalse(moved[:, :3].any())
        self.assertFalse(moved[11:].any())
        np.testing.assert_array_equal(np.asarray(image), pixels)
        self.assertEqual(translate_shared_layer(image, (0, 0)).tobytes(), image.tobytes())
        self.assertFalse(np.asarray(translate_shared_layer(image, (200, 0))).any())

    def test_integer_only(self):
        image = Image.new('RGBA', (11, 13))
        for translation in ((.5, 0), (0, 1.0), (True, 0), (0,), (0, 1, 2), None):
            with self.subTest(translation=translation), self.assertRaises(ValueError):
                translate_shared_layer(image, translation)
        translate_shared_layer(image, (np.int64(2), -3))


class ArmTests(unittest.TestCase):
    def test_length_changes_shaft_not_hand_and_root_is_anchored(self):
        start, wrist = np.array([12., 17.]), np.array([33., 45.])
        axis = (wrist-start)/np.linalg.norm(wrist-start)
        normal = np.array([-axis[1], axis[0]])
        target = np.array([37., 11.])
        mapper = shaft_hand_mapping(start, wrist, length_scale=1.3, width_scale=1.5,
                                    target_start=target, rotation_radians=.7)
        np.testing.assert_allclose(mapper(start), target)
        self.assertAlmostEqual(np.linalg.norm(mapper(wrist)-target), np.linalg.norm(wrist-start)*1.3)
        hand = np.array([wrist+axis*u+normal*v for u, v in [(0, -4), (0, 4), (11, -4), (11, 4), (6, 0)]])
        old_dist = np.linalg.norm(hand[:, None]-hand[None, :], axis=-1)
        new_hand = mapper(hand)
        new_dist = np.linalg.norm(new_hand[:, None]-new_hand[None, :], axis=-1)
        np.testing.assert_allclose(old_dist, new_dist, atol=1e-12)
        center = (start+wrist)/2
        self.assertAlmostEqual(np.linalg.norm(mapper(center+normal*3)-mapper(center-normal*3)), 9)
        np.testing.assert_allclose(mapper(wrist-axis*1e-8), mapper(wrist+axis*1e-8), atol=1e-6)

    def test_two_segment_chain_uses_explicit_parent_endpoint(self):
        shoulder, elbow, wrist = [20, 10], [20, 35], [20, 60]
        upper = shaft_hand_mapping(shoulder, elbow, length_scale=1.2, rotation_radians=-.5)
        fore = shaft_hand_mapping(elbow, wrist, length_scale=1.1,
                                  target_start=upper(elbow), rotation_radians=.8)
        np.testing.assert_allclose(fore(elbow), upper(elbow))
        np.testing.assert_allclose(upper(shoulder), shoulder)
        self.assertAlmostEqual(np.linalg.norm(fore(wrist)-fore(elbow)), 27.5)

    def test_shaft_identity_purity_validation(self):
        points = np.array([[10., 20.], [15., 35.], [20., 100.]])
        original = points.copy()
        np.testing.assert_array_equal(shaft_hand_mapping([10, 20], [15, 35])(points), points)
        np.testing.assert_array_equal(points, original)
        for kwargs in ({'length_scale': 0}, {'length_scale': -1}, {'width_scale': 0},
                       {'rotation_radians': float('nan')}, {'target_start': [3]},
                       {'width_scale': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                shaft_hand_mapping([10, 20], [15, 35], **kwargs)
        with self.assertRaises(ValueError):
            shaft_hand_mapping([10, 20], [10, 20])

    def test_row_centerline_and_whole_root_remain_anchored(self):
        centers = np.linspace(12, 24, 61)
        mapper = row_width_mapping(centers, root_y=9, blend_end_y=23, width_scale=1.6)
        line = np.column_stack([centers, np.arange(61)])
        np.testing.assert_array_equal(mapper(line), line)
        root_band = np.array([[0, 0], [7, 3], [12, 9], [51, 9]])
        np.testing.assert_array_equal(mapper(root_band), root_band)
        pair = np.array([[centers[30]-4, 30], [centers[30]+4, 30]])
        self.assertAlmostEqual(np.diff(mapper(pair)[:, 0])[0], 12.8)
        np.testing.assert_array_equal(mapper(pair)[:, 1], pair[:, 1])
        old = mapper(pair)
        centers[:] = -100
        np.testing.assert_array_equal(mapper(pair), old)

    def test_width_image_arbitrary_canvas_exact_locked_rows_and_no_op(self):
        pixels = np.random.default_rng(4).integers(0, 256, (61, 43, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        centers = np.linspace(19, 24, 61)
        out = widen_rows(image, centers, root_y=9, blend_end_y=23, width_scale=1.6)
        self.assertEqual(out.size, (43, 61))
        np.testing.assert_array_equal(np.asarray(out)[:10], pixels[:10])
        np.testing.assert_array_equal(np.asarray(image), pixels)
        self.assertEqual(widen_rows(image, centers, root_y=9, blend_end_y=23).tobytes(), image.tobytes())
        for kwargs in ({'root_y': 9, 'blend_end_y': 9}, {'root_y': -1, 'blend_end_y': 10},
                       {'root_y': 9, 'blend_end_y': 61}, {'root_y': 9, 'blend_end_y': 10, 'width_scale': -1}):
            with self.assertRaises(ValueError):
                widen_rows(image, centers, **kwargs)
        with self.assertRaises(ValueError):
            widen_rows(image, centers[:-1], root_y=9, blend_end_y=23)
        with self.assertRaises(ValueError):
            row_width_mapping([0, float('nan')], root_y=0, blend_end_y=1)


class TimingAndDemoTests(unittest.TestCase):
    def test_half_open_cycle_actual_time_not_frame_count(self):
        durations = [20, 40, 30]
        schedule = cycle_schedule(durations)
        self.assertEqual(schedule['durationMs'], 90)
        self.assertEqual([f['phase'] for f in schedule['frames']], [0, 2/9, 2/3])
        self.assertEqual([f['startMs'] for f in schedule['frames']], [0, 20, 60])
        self.assertEqual([cycle_frame_at(durations, t) for t in [0, 19.9, 20, 59.9, 60, 89.9, 90, 180, -1]],
                         [0, 0, 1, 1, 2, 2, 0, 0, 2])
        self.assertLess(schedule['frames'][-1]['phase'], 1)
        for d in ([], [0], [25], [float('nan')], [10.0], [True], [-10], None):
            with self.assertRaises(ValueError):
                cycle_schedule(d)
        with self.assertRaises(ValueError):
            cycle_frame_at([10], float('inf'))

    def test_demo_recipe_reproduction_gif_timing_hashes_and_honest_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'one'; second = Path(tmp)/'two'
            manifest = build_demo(out)
            self.assertTrue(manifest['protectedRowsExact'])
            self.assertEqual(manifest['durationMs'], 700)
            recipe = json.loads((out/'recipe.json').read_text())
            self.assertFalse(recipe['quality']['visualApproval'])
            self.assertEqual(recipe['quality']['temporalCertification'], 'BLOCKED / UNREVIEWED')
            for name, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(), digest)
            head = Image.open(out/'shared-head.png').convert('RGBA')
            for record in recipe['registration']:
                i = record['frame']
                body = Image.open(out/f'body-source-{i:02}.png').convert('RGBA')
                result = align_body_axis(body, record['sourceLandmarks'], record['targetLandmarks'], record['lockY'])
                result.alpha_composite(translate_shared_layer(head, record['headTranslation']))
                expected = Image.open(out/f'after-{i:02}.png').convert('RGBA')
                self.assertEqual(result.tobytes(), expected.tobytes())
            for name in ['before.gif', 'after.gif']:
                with Image.open(out/name) as gif:
                    self.assertEqual(gif.n_frames, 8)
                    durations = []
                    for i in range(gif.n_frames):
                        gif.seek(i); durations.append(gif.info['duration'])
                    self.assertEqual(durations, [f['durationMs'] for f in recipe['timing']['frames']])
                    self.assertEqual(sum(durations), manifest['durationMs'])
            self.assertEqual(manifest, build_demo(second))
            self.assertEqual((out/'manifest.json').read_bytes(), (second/'manifest.json').read_bytes())
            with self.assertRaises(ValueError):
                build_demo(out)


if __name__ == '__main__':
    unittest.main()
