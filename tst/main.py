import unittest
from unittest.mock import Mock, MagicMock

import shapely as sh
import shapely.geometry

import shart
from shart.group import Group

class TestMain(unittest.TestCase):

    def test_append_geom(self):
        geom_a = sh.geometry.box(0, 0, 1, 1)
        geom_b = sh.geometry.box(1, 0, 1, 1)
        geom_c = sh.geometry.box(2, 0, 1, 1)

        geom_d = sh.geometry.box(3, 0, 1, 1)

        total_geoms = sh.geometry.MultiPolygon([ geom_a, geom_b, geom_c ])
        total_geoms = shart.utils.append_geom(total_geoms, geom_d)

        self.assertEqual(
                [ g for g in total_geoms.geoms ],
                [ geom_a, geom_b, geom_c, geom_d ])


    def test_anchor_geom(self):
        unanchored = sh.geometry.box(1, 2, 5, 5)

        anchor_fn = shart.utils.anchor_geom(unanchored)

        anchored = anchor_fn(unanchored)

        self.assertEquals(
                sh.geometry.box(0, 0, 4, 3),
                anchored)

    def test_bounds_width(self):
        self.assertEqual(2, Group.rect_centered(0, 0, 2, 3).bounds_width)

    def test_bounds_height(self):
        self.assertEqual(3, Group.rect_centered(0, 0, 2, 3).bounds_height)

    def test_recurse(self):
        geom = Group.rect(0, 0, 10, 10)

        #recursed = geom.recurse(lambda g: [ g.translate(10, 10), g.translate(10, -10) ], 1)

        #self.assertEqual(3, len(recursed.geoms.geoms))

        recursed = geom.recurse(lambda g: [
            g.scale(0.5, 0.5).translate(10, 10),
            g.scale(0.5, 0.5).translate(10, -10) ],
            2)

        #self.assertEqual(7, len(recursed.geoms.geoms))



if __name__ == "__main__":
    unittest.main()
