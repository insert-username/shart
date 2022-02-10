import unittest
from unittest.mock import Mock, MagicMock

import math

import shapely as sh
import shapely.geometry

import shart

class TestMain(unittest.TestCase):

    def test_from_values(self):
        coords = shart.Coordinates([ (0, 1), (2, 3) ])

        self.assertEqual([ c for c in coords ], [ (0, 1), (2, 3) ])

    def test_offfset(self):
        coords = shart.Coordinates([ (0, 1), (2, 3) ])
        coords_offset = coords.offset(dx=1, dy=2)

        self.assertEqual(
                [ c for c in coords_offset ],
                [ (1, 3), (3, 5)  ])

    def test_hex(self):
        coords = [ c for c in shart.Coordinates.hex(3, 3, 1) ]

        self.assertEqual(len(coords), 8)


    def test_polar(self):
        coords = [c for c in shart.Coordinates.polar(6)]

        for c in coords:
            hypot = math.hypot(c[0], c[1])
            self.assertAlmostEqual(hypot, 1)

        self.assertEqual(len(coords), 6)

    def atest_to_polygon(self):
        poly = shart.Coordinates.polar(6).to_group()
        boundary_coords = list(poly.boundary.coords)

        self.assertEqual(len(boundary_coords), 7)
        self.assertEqual(boundary_coords[0], boundary_coords[-1])

        for c in boundary_coords:
            hypot = math.hypot(c[0], c[1])
            self.assertAlmostEquals(hypot, 1)



if __name__ == "__main__":
    unittest.main()
