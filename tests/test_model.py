"""Run with: python -m unittest discover -s tests -p 'test_*.py'."""
import unittest
from controller.model import Instrument, Laser


class ModelTests(unittest.TestCase):
    def test_independent_view_selection(self):
        model = Instrument()
        model.switch_view(1)
        self.assertEqual(model.views, [0, 0])
        model.switch_view(0)
        self.assertEqual(model.views, [1, 0])

    def test_shared_laser_is_one_object(self):
        model = Instrument()
        model.switch_view(1)
        model.laser_for_view(0).set_value('current', '240.125')
        self.assertEqual(model.laser_for_view(1).values['current'], 240.125)
        self.assertEqual(model.lasers[1].values['current'], 229.547)

    def test_invalid_edit_is_atomic(self):
        laser = Laser(1)
        for raw in ('NaN', 'inf', '-1', '501', '', '.', '--2'):
            self.assertTrue(laser.set_value('current', raw))
            self.assertEqual(laser.values['current'], 229.547)

    def test_field_precision_and_negative_pid(self):
        laser = Laser(2)
        self.assertEqual(laser.set_value('pid', '-36.24'), '')
        self.assertEqual(laser.values['pid'], -36.2)
        self.assertEqual(laser.set_value('temperature', '24.125'), '')
        self.assertEqual(laser.values['temperature'], 24.125)

    def test_live_graphs_change_and_stabilisation_reduces_drift(self):
        laser = Laser(1)
        self.assertNotEqual(laser.sample(53.5, 1), laser.sample(53.5, 2))
        drift = abs(laser.drift(1))
        laser.stabilised = True
        self.assertLess(abs(laser.drift(1)), drift / 5)
        laser.locked = True
        self.assertEqual(laser.drift(1), 0)


if __name__ == '__main__':
    unittest.main()
