import unittest
from unittest.mock import Mock, MagicMock

import shapely as sh
import shapely.geometry

import shart
from shart.group import Group

class TestUtils(unittest.TestCase):

    def test_get_interpolated_segment(self):
        l0 = sh.geometry.LineString([(0, 0), (1, 1)])
        l1 = sh.geometry.LineString([(1, 1), (2, 2), (3, 3)])
        l2 = sh.geometry.LineString([(3, 3), (3, 2), (3, 1)])

        mls = sh.geometry.MultiLineString([l0, l1, l2])

        self._assert_line_equals(l0, shart.utils.get_interpolated_segment(mls, 0))
        self._assert_line_equals(
            sh.geometry.LineString([ (1, 1), (2, 2) ]),
            shart.utils.get_interpolated_segment(mls, l1.length))

        self._assert_line_equals(
            sh.geometry.LineString([ (1, 1), (2, 2) ]),
            shart.utils.get_interpolated_segment(mls, l0.length + 0.1 * l1.length))
        self._assert_line_equals(
            sh.geometry.LineString([ (2, 2), (3, 3) ]),
            shart.utils.get_interpolated_segment(mls, l0.length + 0.8 * l1.length))

        self._assert_line_equals(
            sh.geometry.LineString([ (3, 3), (3, 2) ]),
            shart.utils.get_interpolated_segment(mls, l0.length + l1.length + 0.1 * l2.length))

    def _assert_line_equals(self, l0, l1):
        self.assertEqual(list(l0.coords), list(l1.coords))


if __name__ == "__main__":
    unittest.main()
