import copy
import math
import unittest
import numpy as np

from demo import demo
from joint_mesh import joint_mapper
from motion import angle, pose, render, rotate, sub, validate


class WaistAnkleContinuityTests(unittest.TestCase):
    def fixture(self):
        _, rig, layers = demo('side')
        rig.update(walkStyle='simple', motionScale=.4,
                   waistAttachment={'startFraction':0, 'endFraction':.35})
        rig['jointMeshes'] = [{'parent':s+'_thigh', 'child':s+'_shin',
                               'radius':10, 'walkAnkleDepth':20}
                              for s in ('left', 'right')]
        return rig, layers

    def test_default_pixels_preserved(self):
        rig, layers = self.fixture()
        explicit = copy.deepcopy(rig)
        explicit['waistAttachment']['ankleContinuity'] = False
        for phase in (0, .25, .75):
            self.assertEqual(render(rig,layers,'walk',phase)[0].tobytes(),
                             render(explicit,layers,'walk',phase)[0].tobytes())

    def test_opt_in_distal_points_follow_rigid_shoe(self):
        rig, _ = self.fixture()
        rig['waistAttachment']['ankleContinuity'] = True
        validate(rig)
        detected_legacy_difference = False
        for phase in (0, .125, .375, .625, .875):
            transforms, _ = pose(rig,'walk',phase)
            for side in ('left', 'right'):
                shin = rig['parts'][side+'_shin']
                axis = np.array(sub(shin['end'],shin['start']),float)
                axis /= np.linalg.norm(axis)
                normal = np.array([-axis[1],axis[0]])
                point = np.array(shin['end'],float)+axis*4+normal*5
                mapper = joint_mapper(rig,transforms,side+'_thigh',side+'_shin',10,ankle_depth=20)
                actual = mapper(point)
                foot = rig['parts'][side+'_foot']
                dest, theta = transforms[side+'_foot']
                delta = theta-angle(sub(foot['end'],foot['start']))
                expected = np.array(dest)+rotate(sub(point,foot['start']),delta)
                np.testing.assert_allclose(actual,expected,atol=1e-10)
                old = copy.deepcopy(rig)
                old['waistAttachment'].pop('ankleContinuity')
                old_mapper = joint_mapper(old,transforms,side+'_thigh',side+'_shin',10,ankle_depth=20)
                detected_legacy_difference |= np.linalg.norm(old_mapper(point)-actual)>1e-4
        self.assertTrue(detected_legacy_difference)

    def test_validation_and_dash_unchanged(self):
        rig, layers = self.fixture()
        changed = copy.deepcopy(rig)
        changed['waistAttachment']['ankleContinuity'] = True
        # Dash has no walkAnkleDepth, so this flag cannot add a distal transform.
        self.assertEqual(render(rig,layers,'dash',.25)[0].tobytes(),
                         render(changed,layers,'dash',.25)[0].tobytes())
        for bad in (1,0,'true',None):
            changed['waistAttachment']['ankleContinuity'] = bad
            with self.assertRaisesRegex(ValueError,'boolean'):
                validate(changed)


if __name__ == '__main__':
    unittest.main()
