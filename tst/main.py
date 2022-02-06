import unittest
from unittest.mock import Mock, MagicMock

import shapely as sh
import shapely.geometry
import shapely_art_tools as sha

class TestMain(unittest.TestCase):

    def test_append_geom(self):
        geom_a = sh.geometry.box(0, 0, 1, 1)
        geom_b = sh.geometry.box(1, 0, 1, 1)
        geom_c = sh.geometry.box(2, 0, 1, 1)

        geom_d = sh.geometry.box(3, 0, 1, 1)

        total_geoms = sh.geometry.MultiPolygon([ geom_a, geom_b, geom_c ])
        total_geoms = sha.append_geom(total_geoms, geom_d)

        self.assertEqual(
                [ g for g in total_geoms.geoms ],
                [ geom_a, geom_b, geom_c, geom_d ])


    def test_anchor_geom(self):
        unanchored = sh.geometry.box(1, 2, 5, 5)

        anchor_fn = sha.anchor_geom(unanchored)

        anchored = anchor_fn(unanchored)

        self.assertEquals(
                sh.geometry.box(0, 0, 4, 3),
                anchored)






if __name__ == "__main__":
    unittest.main()
