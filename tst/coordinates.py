import unittest
from unittest.mock import Mock, MagicMock

import shapely as sh
import shapely.geometry

import shat

class TestMain(unittest.TestCase):

    def test_from_values(self):
        coords = shat.Coordinates([ (0, 1), (2, 3) ])

        self.assertEquals([ c for c in coords ], [ (0, 1), (2, 3) ])

    def test_offfset(self):
        coords = shat.Coordinates([ (0, 1), (2, 3) ])
        coords_offset = coords.offset(dx=1, dy=2)

        self.assertEquals(
                [ c for c in coords_offset ],
                [ (1, 3), (3, 5)  ])

    def test_hex(self):
        coords = [ c for c in shat.Coordinates.hex(3, 3, 1) ]

        self.assertEquals(len(coords), 8)



if __name__ == "__main__":
    unittest.main()
