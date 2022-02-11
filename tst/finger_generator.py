import unittest
from unittest.mock import Mock, MagicMock

import math

import shapely as sh
import shapely.geometry

import numpy as np
import numpy.testing

import shart


class TestMain(unittest.TestCase):

    def test_no_phase(self):
        ic = shart.IntervalCalculator(1, 0.5, 0)

        intervals = ic.get_intervals(3)

        self.assertEqual([
            ((0, 0.5), (0.5, 1)),
            ((1, 1.5), (1.5, 2)),
            ((2, 2.5), (2.5, 3))
        ], intervals)

    def test_duty(self):
        ic = shart.IntervalCalculator(1, 0.3, 0)

        intervals = ic.get_intervals(3)

        self.assertEqual([
            ((0, 0.3), (0.3, 1)),
            ((1, 1.3), (1.3, 2)),
            ((2, 2.3), (2.3, 3))
        ], intervals)

    def test_phase_1(self):
        ic = shart.IntervalCalculator(1, 0.5, 0.25)

        intervals = ic.get_intervals(3)

        self.assertEqual([
            ((-0.75, -0.25), (-0.25, 0.25)),
            ((0.25, 0.75), (0.75, 1.25)),
            ((1.25, 1.75), (1.75, 2.25)),
            ((2.25, 2.75), (2.75, 3.25))
        ], intervals)

    def test_phase_2(self):
        ic = shart.IntervalCalculator(1, 0.5, 0.3)

        intervals = ic.get_intervals(3)

        np.testing.assert_almost_equal(intervals, [
            ((-0.7, -0.2), (-0.2, 0.3)),
            ((0.3, 0.8), (0.8, 1.3)),
            ((1.3, 1.8), (1.8, 2.3)),
            ((2.3, 2.8), (2.8, 3.3))
        ])


if __name__ == "__main__":
    unittest.main()
