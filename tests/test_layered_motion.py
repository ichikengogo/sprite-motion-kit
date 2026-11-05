"""Synthetic fixtures only; no user artwork or private calibration."""
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw

from layered_motion import (chain_mapper, fit_periodic_support_height, main, limb_phase, load_manifest,
                            project_forward, render_frame, support_height_offset,
                            warp_layer, write_demo)


class LayeredMotionTests(unittest.TestCase):
    def test_physical_phase_is_camera_independent_and_opposed(self):
        for phase in (0, .17, .5, .91, 1):
            self.assertAlmostEqual(limb_phase(phase, 'left', 'arm'), limb_phase(phase, 'right', 'leg'))
            self.assertAlmostEqual((limb_phase(phase, 'left', 'arm') - limb_phase(phase, 'left', 'leg')) % 1, .5)
        np.testing.assert_allclose(project_forward(4, 'side_left'), [-4, 0])
        np.testing.assert_allclose(project_forward(4, 'front'), -project_forward(4, 'back'))
        with self.assertRaises(ValueError):
            limb_phase(0, 'near')

    def test_support_fit_uses_supplied_stance_geometry(self):
        support = {'hip': [10, 10], 'ankle': [10, 35], 'lengths': [10, 10]}
        self.assertEqual(support_height_offset([support]), 5)
        support['ankle'] = [22, 26]
        self.assertAlmostEqual(support_height_offset([support]), 0)
        support['ankle'] = [31, 26]
        with self.assertRaises(ValueError):
            support_height_offset([support])
        with self.assertRaises(ValueError):
            support_height_offset([])

    def test_socket_band_is_bounded_and_attached(self):
        rest = [[10, 10], [10, 20], [10, 30]]
        posed = [[10, 10], [16, 20], [20, 30]]
        blended = chain_mapper(rest, posed, root_blend=5)
        full = chain_mapper(rest, posed)
        np.testing.assert_allclose(blended([7, 10]), [7, 10])
        np.testing.assert_allclose(blended([7, 8]), [7, 8])
        np.testing.assert_allclose(blended([7, 15]), full([7, 15]))
        for y in np.linspace(10, 15, 20):
            value, original = blended([10, y]), full([10, y])
            self.assertGreaterEqual(value[0], 10)
            self.assertLessEqual(value[0], original[0] + 1e-9)

    def test_invalid_chains_fail(self):
        for rest in ([[[0, 0]]], [[0, 1], [0, 0]], [[0, 0], [math.nan, 2]]):
            with self.assertRaises(ValueError):
                chain_mapper(rest, rest)

    def test_identity_and_translation_non_square_canvas(self):
        image = Image.new('RGBA', (37, 25))
        ImageDraw.Draw(image).rectangle((3, 4, 9, 12), fill=(20, 80, 140, 170))
        result = warp_layer(image, lambda point: point, step=3)
        np.testing.assert_array_equal(result, image)
        shifted = warp_layer(image, lambda point: point + [4, 2], step=4)
        expected = Image.new('RGBA', image.size)
        expected.paste(image, (4, 2))
        np.testing.assert_array_equal(shifted, expected)

    def test_transparent_edge_does_not_leak_rgb(self):
        image = Image.new('RGBA', (12, 12), (255, 0, 0, 0))
        ImageDraw.Draw(image).rectangle((3, 3, 8, 8), fill=(0, 255, 0, 255))
        result = np.asarray(warp_layer(image, lambda point: point + [.3, .2], step=2))
        visible = result[..., 3] > 0
        self.assertTrue(np.all(result[..., 0][visible] == 0))
        self.assertTrue(np.all(result[..., 1][visible] == 255))

    def test_fold_rejected_and_empty_preserved(self):
        image = Image.new('RGBA', (10, 10), 'red')
        with self.assertRaises(ValueError):
            warp_layer(image, lambda point: point * [-1, 1])
        blank = Image.new('RGBA', (7, 11))
        self.assertEqual(warp_layer(blank, lambda point: point).size, (7, 11))

    def test_manifest_paths_and_layer_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGBA', (8, 8), 'red').save(root / 'red.png')
            Image.new('RGBA', (8, 8), 'blue').save(root / 'blue.png')
            manifest = {'version': 1, 'canvas': [8, 8], 'layers': [
                {'name': 'red', 'file': 'red.png'}, {'name': 'blue', 'file': 'blue.png'}],
                'frames': [{}, {'order': ['blue', 'red']}]}
            path = root / 'manifest.json'
            path.write_text(json.dumps(manifest))
            loaded, assets = load_manifest(path)
            self.assertEqual(render_frame(loaded, assets, 0).getpixel((4, 4)), (0, 0, 255, 255))
            self.assertEqual(render_frame(loaded, assets, 1).getpixel((4, 4)), (255, 0, 0, 255))
            loaded['frames'][0]['order'] = ['red', 'red']
            with self.assertRaises(ValueError):
                render_frame(loaded, assets, 0)
            manifest['layers'][0]['file'] = '../outside.png'
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_periodic_support_fit_full_cycle_and_boundary(self):
        def curve(phase):
            return 2 + 1.5 * math.sin(2 * math.pi * phase) + .4 * math.cos(4 * math.pi * phase)
        samples = [{'phase': phase, 'supports': [
            {'hip': [0, 0], 'ankle': [0, 20 + curve(phase)], 'lengths': [10, 10]}]}
            for phase in np.linspace(0, 1, 16, endpoint=False)]
        fitted = fit_periodic_support_height(samples, harmonics=2)
        for phase in np.linspace(-1, 2, 121):
            self.assertAlmostEqual(fitted(phase), curve(phase), places=10)
        self.assertEqual(fitted(0), fitted(1))
        epsilon = 1e-6
        slope_before = (fitted(0) - fitted(-epsilon)) / epsilon
        slope_after = (fitted(epsilon) - fitted(0)) / epsilon
        self.assertAlmostEqual(slope_before, slope_after, places=3)
        self.assertLess(fitted.diagnostics['max_abs_vertical_residual'], 1e-10)
        self.assertGreater(fitted.diagnostics['minimum_fitted_straight_leg_reach_margin'], -1e-10)

    def test_periodic_exchange_conflicts_report_residual_and_overreach(self):
        samples = [{'phase': 0, 'supports': [
            {'hip': [0, 0], 'ankle': [0, 20], 'lengths': [10, 10], 'weight': 1},
            {'hip': [0, 0], 'ankle': [0, 24], 'lengths': [10, 10], 'weight': 3}]}]
        fitted = fit_periodic_support_height(samples, harmonics=0)
        self.assertAlmostEqual(fitted(.7), 3)
        self.assertAlmostEqual(fitted.diagnostics['weighted_rms_vertical_residual'], math.sqrt(3))
        self.assertAlmostEqual(fitted.diagnostics['max_abs_vertical_residual'], 3)
        self.assertAlmostEqual(fitted.diagnostics['minimum_fitted_straight_leg_reach_margin'], -1)
        self.assertEqual(len(fitted.diagnostics['constraints']), 2)

    def test_periodic_support_rejects_bad_constraints(self):
        support = {'hip': [0, 0], 'ankle': [0, 20], 'lengths': [10, 10]}
        for samples, harmonics in [([], 0), ([{'phase': 0, 'supports': []}], 0),
                ([{'phase': math.nan, 'supports': [support]}], 0),
                ([{'phase': 0, 'supports': [support]}], -1),
                ([{'phase': 0, 'supports': [support]}], 1),
                ([{'phase': i, 'supports': [support]} for i in range(4)], 1),
                ([{'phase': 0, 'supports': [dict(support, stance=False)]}], 0),
                ([{'phase': 0, 'supports': [dict(support, weight=0)]}], 0),
                ([{'phase': 0, 'supports': [dict(support, ankle=[30, 20])]}], 0)]:
            with self.assertRaises(ValueError):
                fit_periodic_support_height(samples, harmonics)
        fitted = fit_periodic_support_height([{'phase': 0, 'supports': [support]}], 0)
        with self.assertRaises(ValueError):
            fitted(math.inf)

    def test_demo_and_renderer_refuse_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / 'frame-0000.png'
            marker.write_bytes(b'keep existing artifact')
            with self.assertRaises(ValueError):
                write_demo(root)
            self.assertEqual(marker.read_bytes(), b'keep existing artifact')
            source = root / 'source'
            write_demo(source, frame_count=4)
            with self.assertRaises(ValueError):
                main([str(source / 'front' / 'manifest.json'), str(root)])
            self.assertEqual(marker.read_bytes(), b'keep existing artifact')

    def test_original_demo_loop_omits_duplicate_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            write_demo(directory, frame_count=4)
            for view in ('front', 'side_right', 'back'):
                root = Path(directory) / view
                manifest, assets = load_manifest(root / 'manifest.json')
                self.assertEqual([frame['phase'] for frame in manifest['frames']], [0, .25, .5, .75])
                self.assertEqual(len(list(root.glob('frame-*.png'))), 4)
                self.assertFalse(np.array_equal(render_frame(manifest, assets, 0), render_frame(manifest, assets, 3)))
                with Image.open(root / 'preview.gif') as preview:
                    self.assertEqual(preview.n_frames, 4)


if __name__ == '__main__':
    unittest.main()
