import copy
import math
import unittest

from demo import demo
from motion import angle, pose, render, rotate, sub, validate


class HeldSourceArmsTests(unittest.TestCase):
    def test_held_landmarks_follow_torso_at_every_phase(self):
        _, rig, _ = demo('side')
        rig.update(armPose='held-source', walkStyle='simple',
                   walkPosture='upright', motionScale=.4)
        # Bent, strap-gripping source arms, not a lowered neutral-arm example.
        for i, side in enumerate(('left', 'right')):
            shoulder = [185 + i * 12, 151]
            elbow = [205 + i * 12, 184]
            wrist = [179 + i * 12, 164]
            rig['parts'][side + '_upper_arm'].update(start=shoulder, end=elbow)
            rig['parts'][side + '_forearm'].update(start=elbow, end=wrist)
        validate(rig)
        for phase in range(24):
            transforms, diagnostics = pose(rig, 'walk', phase / 24)
            torso = rig['parts']['torso']
            dest, theta = transforms['torso']
            delta = theta - angle(sub(torso['end'], torso['start']))
            def expected(point):
                offset = rotate(sub(point, torso['start']), delta)
                return [dest[j] + offset[j] for j in range(2)]
            for side in ('left', 'right'):
                for part_name in ('upper_arm', 'forearm'):
                    name = side + '_' + part_name
                    part = rig['parts'][name]
                    actual_start, actual_angle = transforms[name]
                    for a, b in zip(actual_start, expected(part['start'])):
                        self.assertAlmostEqual(a, b, places=10)
                    source_length = math.hypot(*sub(part['end'], part['start']))
                    actual_end = [actual_start[0] + source_length * math.cos(actual_angle),
                                  actual_start[1] + source_length * math.sin(actual_angle)]
                    for a, b in zip(actual_end, expected(part['end'])):
                        self.assertAlmostEqual(a, b, places=10)
                diagnostic = next(d for d in diagnostics if d['side'] == side)
                self.assertEqual(diagnostic['armPose'], 'held-source')
                for a, b in zip(diagnostic['wrist'], expected(rig['parts'][side + '_forearm']['end'])):
                    self.assertAlmostEqual(a, b, places=10)

    def test_legacy_default_and_dash_unchanged(self):
        _, rig, layers = demo('side')
        legacy = copy.deepcopy(rig)
        legacy['armPose'] = 'legacy'
        held = copy.deepcopy(rig)
        held['armPose'] = 'held-source'
        for phase in (0, .125, .375, .625, .875):
            self.assertEqual(pose(rig, 'walk', phase), pose(legacy, 'walk', phase))
            self.assertEqual(render(rig, layers, 'walk', phase)[0].tobytes(),
                             render(legacy, layers, 'walk', phase)[0].tobytes())
            self.assertEqual(pose(rig, 'dash', phase), pose(held, 'dash', phase))

    def test_validation(self):
        for view in ('front', 'back'):
            _, rig, _ = demo(view)
            rig['armPose'] = 'held-source'
            with self.assertRaisesRegex(ValueError, 'side view'):
                validate(rig)
        _, rig, _ = demo('side')
        for invalid in ('held', '', None, False):
            rig['armPose'] = invalid
            with self.assertRaisesRegex(ValueError, 'Unknown armPose'):
                validate(rig)


if __name__ == '__main__':
    unittest.main()
